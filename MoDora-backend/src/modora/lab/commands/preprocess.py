from __future__ import annotations

import asyncio
import argparse
import concurrent.futures as futures
import json
import logging
import os
from pathlib import Path
import time
from typing import Any

from tqdm import tqdm

from modora.core.preprocess import get_components_async
from modora.core.settings import Settings
from modora.core.domain.jobs import PreprocessJob
from modora.core.domain.ocr import OcrExtractResponse, OCRBlock
from modora.core.infra.ocr.manager import ensure_ocr_model_loaded, get_ocr_model
from modora.core.infra.pdf.fallback import extract_pdf_blocks
from modora.core.infra.logging.setup import configure_logging
from modora.core.infra.llm import ensure_llm_local_loaded, shutdown_llm_local
from modora.core.utils.fs import iter_pdf_paths
from modora.core.utils.pydantic import pydantic_dump, pydantic_validate
from modora.core.utils.config import load_ui_settings_from_config


def _component_worker_wrapper(
    res_path: str, co_path: str, config_path: str | None
) -> tuple[int, int, float]:
    """Component extraction worker function.

    Runs in a separate process to avoid GIL and segmentation fault issues
    caused by C extensions (e.g., fitz).

    Args:
        res_path: Path to the OCR results file.
        co_path: Path to save the extracted components.
        config_path: Path to the configuration file.

    Returns:
        A tuple containing (number of blocks, number of components, elapsed time).
    """

    logger = logging.getLogger("modora.preprocess.worker")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

    # Run asynchronous logic in the worker process's own event loop
    return asyncio.run(_run_get_components(res_path, co_path, logger, config_path))


def _ocr_worker_run(
    pdf_path: str, config_path: str | None = None
) -> tuple[dict[str, Any], int, float]:
    """Worker function to execute OCR tasks.

    Args:
        pdf_path: Path to the PDF file.
        config_path: Path to the configuration file.

    Returns:
        A tuple containing (OCR payload, number of blocks, elapsed time).
    """
    t0 = time.monotonic()
    logger = logging.getLogger("modora.preprocess.ocr_worker")

    # Ensure configuration is reloaded and OCR model is initialized
    settings = Settings.load(config_path)
    ensure_ocr_model_loaded(settings, logger)

    model = get_ocr_model()
    if model is None:
        raise RuntimeError("OCR model not loaded")

    try:
        pdf_blocks: list[OCRBlock] = []
        source = f"file:{pdf_path}"
        for page_blocks in model.predict_iter(pdf_path):
            pdf_blocks.extend(page_blocks)
        ocr_res = OcrExtractResponse(source=source, blocks=pdf_blocks)
    except Exception as e:
        logger.warning(
            "ocr predict failed, using pdf text fallback",
            extra={"task_name": "ocr", "pdf": pdf_path, "error": str(e)},
            exc_info=True,
        )
        ocr_res = extract_pdf_blocks(pdf_path)
    payload = pydantic_dump(ocr_res)
    blocks = payload.get("blocks") if isinstance(payload, dict) else None
    n_blocks = len(blocks) if isinstance(blocks, list) else 0
    return payload, n_blocks, time.monotonic() - t0


async def _run_get_components(
    res_path: str, co_path: str, logger: logging.Logger, config_path: str | None
) -> tuple[int, int, float]:
    """Run component extraction logic.

    Extracts document components from OCR results and saves them.

    Args:
        res_path: Path to the OCR results file.
        co_path: Path to save the extracted components.
        logger: Logger instance.

    Returns:
        A tuple containing (number of blocks, number of body components, elapsed time).
    """
    t0 = time.monotonic()
    obj = json.loads(Path(res_path).read_text(encoding="utf-8"))
    ocr_res = pydantic_validate(OcrExtractResponse, obj)
    blocks_n = len(getattr(ocr_res, "blocks", []) or [])
    ui_settings = load_ui_settings_from_config(config_path)
    co_pack = await get_components_async(ocr_res, logger, config=ui_settings)
    body_n = len(co_pack.body)
    co_pack.save_json(co_path)
    return blocks_n, body_n, time.monotonic() - t0


def register(sub: argparse._SubParsersAction) -> None:
    """Register the ocr subcommand.

    Args:
        sub: The sub-parsers action to add the parser to.
    """
    p = sub.add_parser("ocr", help="Run OCR+get_component for dataset PDFs")
    p.add_argument(
        "--dataset",
        default=None,
        help="Path to a PDF file or directory",
    )
    p.add_argument(
        "--cache-dir",
        default=None,
        help="Cache directory (writes <num>/res.json and <num>/co.json)",
    )
    p.add_argument(
        "--component-workers",
        type=int,
        default=64,
        help="Number of get_component workers (threads)",
    )
    p.add_argument(
        "--ocr-batch-size",
        type=int,
        default=1,
        help="Text recognition batch size for OCR. Increasing this can improve GPU throughput.",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Skip steps whose output files already exist",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing res.json/co.json (disables resume)",
    )
    p.set_defaults(_handler=_handle_preprocess_ocr_pipeline)


class PreprocessPipeline:
    """Preprocessing pipeline: PDF -> OCR (single-threaded) -> Components (multi-processed).

    Supports resume and process pool failure recovery.
    """

    def __init__(
        self,
        args: argparse.Namespace,
        settings: Settings,
        logger: logging.Logger,
        config_path: str | None,
    ):
        self.args = args
        self.settings = settings
        self.logger = logger
        self.config_path = config_path

        self.cache_dir = str(getattr(args, "cache_dir", "cache"))
        self.component_workers = int(getattr(args, "component_workers", 8) or 1)
        self.resume = bool(getattr(args, "resume", False)) and not bool(
            getattr(args, "overwrite", False)
        )

        self.jobs: list[PreprocessJob] = []
        self.total = 0
        self.done_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.pbar: tqdm | None = None

        # Concurrency control
        self.current_pool: futures.ProcessPoolExecutor | None = None
        self.pool_lock = asyncio.Lock()
        self.submit_sem = asyncio.Semaphore(self.component_workers)
        self.co_tasks: dict[asyncio.Task, PreprocessJob] = {}

    def _tick(self, is_fail: bool = False, is_skip: bool = False) -> None:
        """Update progress bar and counters.

        Args:
            is_fail: Whether the current job failed.
            is_skip: Whether the current job was skipped.
        """
        self.done_count += 1
        if is_fail:
            self.failed_count += 1
        if is_skip:
            self.skipped_count += 1
        if self.pbar:
            self.pbar.update(1)
            self.pbar.set_postfix(
                success=self.done_count - self.failed_count - self.skipped_count,
                failed=self.failed_count,
                skipped=self.skipped_count,
                refresh=False,
            )

    def prepare_jobs(self) -> list[PreprocessJob]:
        """Prepare the list of jobs.

        Returns:
            A list of PreprocessJob instances.
        """
        pdf_paths = list(iter_pdf_paths(str(self.args.dataset)))
        if not pdf_paths:
            return []

        os.makedirs(self.cache_dir, exist_ok=True)
        self.jobs = [
            PreprocessJob(
                idx=i,
                pdf_path=str(pdf_path),
                out_dir=os.path.join(self.cache_dir, str(i)),
                res_path=os.path.join(self.cache_dir, str(i), "res.json"),
                co_path=os.path.join(self.cache_dir, str(i), "co.json"),
            )
            for i, pdf_path in enumerate(pdf_paths, start=1)
        ]
        self.total = len(self.jobs)
        return self.jobs

    async def run_ocr_stage(self, job: PreprocessJob) -> bool:
        """Execute the OCR stage for a given job.

        Args:
            job: The preprocessing job to execute.

        Returns:
            True if the OCR stage was successful or skipped, False otherwise.
        """
        os.makedirs(job.out_dir, exist_ok=True)
        res_exists = os.path.isfile(job.res_path)
        co_exists = os.path.isfile(job.co_path)

        if self.resume and res_exists and co_exists:
            self._tick(is_skip=True)
            return False

        if not res_exists or not self.resume:
            try:
                loop = asyncio.get_running_loop()
                # Run OCR directly in the main process (using thread pool)
                # to avoid CUDA initialization issues with fork.
                payload, _, _ = await loop.run_in_executor(
                    None, _ocr_worker_run, job.pdf_path, self.config_path
                )
                await loop.run_in_executor(
                    None,
                    lambda: Path(job.res_path).write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    ),
                )
                return True
            except Exception as e:
                self.logger.error(
                    "ocr failed",
                    extra={"task_name": "ocr", "pdf": job.pdf_path, "error": str(e)},
                    exc_info=True,
                )
                self._tick(is_fail=True)
                self.logger.error(
                    f"FAILED_PDF_ID: {job.idx}",
                    extra={"task_name": "preprocess", "pdf_id": job.idx},
                )
                return False
            finally:
                pass
        return True

    async def _submit_component_job(self, job: PreprocessJob, retry: int = 0):
        """Submit component extraction task to process pool with retry and recovery logic.

        Args:
            job: The preprocessing job to submit.
            retry: Current retry count. Defaults to 0.
        """
        await self.submit_sem.acquire()
        try:
            loop = asyncio.get_running_loop()
            async with self.pool_lock:
                if self.current_pool is None or getattr(
                    self.current_pool, "_broken", False
                ):
                    if self.current_pool:
                        self.logger.warning(
                            "ProcessPool broken, restarting...",
                            extra={"task_name": "preprocess"},
                        )
                        self.current_pool.shutdown(wait=False)
                    self.current_pool = futures.ProcessPoolExecutor(
                        max_workers=self.component_workers
                    )
                pool = self.current_pool

            return await loop.run_in_executor(
                pool,
                _component_worker_wrapper,
                job.res_path,
                job.co_path,
                self.config_path,
            )
        except futures.process.BrokenProcessPool:
            if retry >= 1:
                raise
            self.logger.warning(
                f"Job {job.idx} encountered BrokenProcessPool, retrying...",
                extra={"task_name": "preprocess"},
            )
            return await self._submit_component_job(job, retry=retry + 1)
        finally:
            self.submit_sem.release()

    def _handle_task_done(self, t: asyncio.Task):
        """Handle the completion of a component extraction task."""
        if t not in self.co_tasks:
            return
        job = self.co_tasks.pop(t)
        try:
            t.result()
            self._tick()
        except Exception as e:
            self.logger.error(
                "get_component failed",
                extra={
                    "task_name": "get_component",
                    "pdf": job.pdf_path,
                    "error": str(e),
                },
                exc_info=True,
            )
            self._tick(is_fail=True)
            self.logger.error(
                f"FAILED_PDF_ID: {job.idx}",
                extra={"task_name": "preprocess", "pdf_id": job.idx},
            )

    async def run(self) -> int:
        """Run the preprocessing pipeline.

        Returns:
            0 if successful, 2 if there were failures.
        """
        jobs = self.prepare_jobs()
        if not jobs:
            self.logger.error("no pdf files found")
            return 2

        self.pbar = tqdm(
            total=self.total, unit="pdf", dynamic_ncols=True, disable=False
        )
        self.pbar.set_postfix(
            success=self.done_count - self.failed_count - self.skipped_count,
            failed=self.failed_count,
            skipped=self.skipped_count,
            refresh=False,
        )

        # Preload OCR model in the main process.
        ensure_ocr_model_loaded(self.settings, self.logger)

        cancelled = False
        try:
            # Start all tasks in parallel.
            ocr_tasks = []
            for job in jobs:
                ocr_tasks.append(asyncio.create_task(self._process_full_pipeline(job)))

            if ocr_tasks:
                await asyncio.gather(*ocr_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            cancelled = True
            raise

        finally:
            if self.current_pool:
                if cancelled:
                    self.current_pool.shutdown(wait=False, cancel_futures=True)
                else:
                    self.current_pool.shutdown(wait=True)
            if self.pbar:
                self.pbar.close()

        return 2 if self.failed_count else 0

    async def _process_full_pipeline(self, job: PreprocessJob):
        """Process the full pipeline for a single PDF (OCR + Component extraction).

        Args:
            job: The preprocessing job to execute.
        """
        if self.pbar:
            self.pbar.set_description(Path(job.pdf_path).name, refresh=False)
        if await self.run_ocr_stage(job):
            task = asyncio.create_task(self._submit_component_job(job))
            self.co_tasks[task] = job
            task.add_done_callback(self._handle_task_done)
            await task


def _handle_preprocess_ocr_pipeline(
    args: argparse.Namespace, logger: logging.Logger
) -> int:
    """Entry point for the preprocessing pipeline.

    Args:
        args: Command line arguments.
        logger: Logger instance.

    Returns:
        The exit code of the pipeline.
    """
    config_path = (getattr(args, "config", None) or "").strip() or None
    if config_path:
        os.environ["MODORA_CONFIG"] = config_path

    # Override environment variable/config if batch-size is specified in CLI.
    if getattr(args, "ocr_batch_size", None) is not None:
        os.environ["MODORA_OCR_TEXT_RECOGNITION_BATCH_SIZE"] = str(args.ocr_batch_size)

    settings = Settings.load(config_path)
    configure_logging(settings)
    ensure_llm_local_loaded(settings, logger)

    try:
        if not getattr(args, "dataset", None):
            args.dataset = settings.docs_dir
        if not getattr(args, "cache_dir", None):
            args.cache_dir = settings.cache_dir
        pipeline = PreprocessPipeline(args, settings, logger, config_path)
        result = asyncio.run(pipeline.run())

        status = "finished with failures" if result == 2 else "finished"
        log_fn = logger.error if result == 2 else logger.info
        log_fn(
            f"preprocess ocr pipeline {status}",
            extra={
                "task_name": "preprocess",
                "total": pipeline.total,
                "failed": pipeline.failed_count,
                "cache_dir": pipeline.cache_dir,
            },
        )
        return result
    finally:
        shutdown_llm_local()
