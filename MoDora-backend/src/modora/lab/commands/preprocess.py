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
from modora.core.infra.logging.setup import configure_logging
from modora.core.infra.llm import ensure_llm_local_loaded, shutdown_llm_local
from modora.core.utils.fs import iter_pdf_paths
from modora.core.utils.pydantic import pydantic_dump, pydantic_validate


def _component_worker_wrapper(
    res_path: str, co_path: str, config_path: str | None
) -> tuple[int, int, float]:
    """
    组件提取工作函数。
    在单独的进程中运行，以避免 C 扩展（如 fitz）导致的 GIL 和段错误问题。
    """

    logger = logging.getLogger("modora.preprocess.worker")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

    # 在工作进程自己的事件循环中运行异步逻辑
    return asyncio.run(_run_get_components(res_path, co_path, logger))


def _ocr_worker_run(pdf_path: str, config_path: str | None = None) -> tuple[dict[str, Any], int, float]:
    """执行 OCR 任务的工作函数"""
    t0 = time.monotonic()

    # 确保在子进程中重新加载配置并初始化 OCR 模型
    settings = Settings.load(config_path)
    ensure_ocr_model_loaded(settings, logging.getLogger("modora.preprocess.ocr_worker"))

    model = get_ocr_model()
    if model is None:
        raise RuntimeError("OCR model not loaded")

    pdf_blocks: list[OCRBlock] = []
    source = f"file:{pdf_path}"
    for page_blocks in model.predict_iter(pdf_path):
        pdf_blocks.extend(page_blocks)

    ocr_res = OcrExtractResponse(source=source, blocks=pdf_blocks)
    payload = pydantic_dump(ocr_res)
    blocks = payload.get("blocks") if isinstance(payload, dict) else None
    n_blocks = len(blocks) if isinstance(blocks, list) else 0
    return payload, n_blocks, time.monotonic() - t0


async def _run_get_components(
    res_path: str, co_path: str, logger: logging.Logger
) -> tuple[int, int, float]:
    """运行组件提取逻辑：从 OCR 结果中提取文档组件并保存"""
    t0 = time.monotonic()
    obj = json.loads(Path(res_path).read_text(encoding="utf-8"))
    ocr_res = pydantic_validate(OcrExtractResponse, obj)
    blocks_n = len(getattr(ocr_res, "blocks", []) or [])
    co_pack = await get_components_async(ocr_res, logger)
    body_n = len(co_pack.body)
    co_pack.save_json(co_path)
    return blocks_n, body_n, time.monotonic() - t0


def register(sub: argparse._SubParsersAction) -> None:
    """注册 ocr 子命令"""
    p = sub.add_parser("ocr", help="Run OCR+get_component for dataset PDFs")
    p.add_argument(
        "--dataset",
        default="/home/yukai/project/MoDora/datasets/MMDA",
        help="Path to a PDF file or directory",
    )
    p.add_argument(
        "--cache-dir",
        default="cache_v4",
        help="Cache directory (writes <num>/res.json and <num>/co.json)",
    )
    p.add_argument(
        "--component-workers",
        type=int,
        default=64,
        help="Number of get_component workers (threads)",
    )
    p.add_argument(
        "--ocr-workers",
        type=int,
        default=1,
        help="Number of parallel OCR workers (processes). Set > 1 only if you have enough GPU memory.",
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
    """
    预处理流水线：PDF -> OCR (单线程) -> Components (多进程)。
    支持断点续传和进程池故障恢复。
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
        self.ocr_workers = int(getattr(args, "ocr_workers", 1) or 1)
        self.resume = bool(getattr(args, "resume", False)) and not bool(
            getattr(args, "overwrite", False)
        )

        self.jobs: list[PreprocessJob] = []
        self.total = 0
        self.done_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.pbar: tqdm | None = None

        # 并发控制
        self.current_pool: futures.ProcessPoolExecutor | None = None
        self.ocr_pool: futures.ProcessPoolExecutor | None = None
        self.pool_lock = asyncio.Lock()
        self.submit_sem = asyncio.Semaphore(self.component_workers)
        self.ocr_sem = asyncio.Semaphore(self.ocr_workers)
        self.co_tasks: dict[asyncio.Task, PreprocessJob] = {}

    def _tick(self, is_fail=False, is_skip=False) -> None:
        """更新进度条和计数器"""
        self.done_count += 1
        if is_fail:
            self.failed_count += 1
        if is_skip:
            self.skipped_count += 1
        if self.pbar:
            self.pbar.update(1)
            self.pbar.set_postfix(
                failed=self.failed_count, skipped=self.skipped_count, refresh=False
            )

    def prepare_jobs(self) -> list[PreprocessJob]:
        """准备任务列表"""
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
        """执行 OCR 阶段"""
        os.makedirs(job.out_dir, exist_ok=True)
        res_exists = os.path.isfile(job.res_path)
        co_exists = os.path.isfile(job.co_path)

        if self.resume and res_exists and co_exists:
            self.logger.info(
                "pdf done (skipped)",
                extra={
                    "task_name": "get_component",
                    "pdf": job.pdf_path,
                    "res": job.res_path,
                    "co": job.co_path,
                },
            )
            self._tick(is_skip=True)
            return False

        if not res_exists or not self.resume:
            await self.ocr_sem.acquire()
            try:
                loop = asyncio.get_running_loop()
                async with self.pool_lock:
                    if self.ocr_pool is None:
                        self.ocr_pool = futures.ProcessPoolExecutor(
                            max_workers=self.ocr_workers
                        )
                    pool = self.ocr_pool

                payload, _, _ = await loop.run_in_executor(
                    pool, _ocr_worker_run, job.pdf_path, self.config_path
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
                self.ocr_sem.release()
        return True

    async def _submit_component_job(self, job: PreprocessJob, retry=0):
        """提交组件提取任务到进程池，包含重试和进程池恢复逻辑"""
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
        """处理组件提取任务完成后的回调"""
        if t not in self.co_tasks:
            return
        job = self.co_tasks.pop(t)
        try:
            t.result()
            self.logger.info(
                "pdf done",
                extra={
                    "task_name": "get_component",
                    "pdf": job.pdf_path,
                    "res": job.res_path,
                    "co": job.co_path,
                },
            )
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
        """运行流水线"""
        jobs = self.prepare_jobs()
        if not jobs:
            self.logger.error("no pdf files found")
            return 2

        self.pbar = tqdm(total=self.total, unit="pdf", dynamic_ncols=True)
        self.pbar.set_postfix(
            failed=self.failed_count, skipped=self.skipped_count, refresh=False
        )

        # 在主进程预加载 OCR 模型（如果是单线程模式）
        if self.ocr_workers == 1:
            ensure_ocr_model_loaded(self.settings, self.logger)

        try:
            # 所有的任务并行启动
            ocr_tasks = []
            for job in jobs:
                ocr_tasks.append(asyncio.create_task(self._process_full_pipeline(job)))

            if ocr_tasks:
                await asyncio.gather(*ocr_tasks, return_exceptions=True)

        finally:
            if self.current_pool:
                self.current_pool.shutdown(wait=True)
            if self.ocr_pool:
                self.ocr_pool.shutdown(wait=True)
            if self.pbar:
                self.pbar.close()

        return 2 if self.failed_count else 0

    async def _process_full_pipeline(self, job: PreprocessJob):
        """处理单个 PDF 的完整流水线（OCR + Component）"""
        if await self.run_ocr_stage(job):
            task = asyncio.create_task(self._submit_component_job(job))
            self.co_tasks[task] = job
            task.add_done_callback(self._handle_task_done)
            await task


def _handle_preprocess_ocr_pipeline(
    args: argparse.Namespace, logger: logging.Logger
) -> int:
    """预处理流水线入口"""
    config_path = (getattr(args, "config", None) or "").strip() or None
    if config_path:
        os.environ["MODORA_CONFIG"] = config_path

    # 如果 CLI 指定了 batch-size，则覆盖环境变量/配置
    if getattr(args, "ocr_batch_size", None) is not None:
        os.environ["MODORA_OCR_TEXT_RECOGNITION_BATCH_SIZE"] = str(args.ocr_batch_size)

    settings = Settings.load(config_path)
    configure_logging(settings)
    ensure_llm_local_loaded(settings, logger)

    try:
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
