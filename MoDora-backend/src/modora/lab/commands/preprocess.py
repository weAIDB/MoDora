from __future__ import annotations

import asyncio
import argparse
import concurrent.futures as futures
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import time
from typing import Any

from tqdm import tqdm

from modora.core.preprocess import get_components_async
from modora.core.settings import Settings
from modora.core.domain.ocr import OcrExtractResponse
from modora.service.api.ocr.router import (
    OCRExtractPdfRequest,
    ocr_extract_pdf,
)
from modora.core.infra.ocr.manager import ensure_ocr_model_loaded
from modora.core.infra.logging.setup import configure_logging


def _component_worker_wrapper(
    res_path: str, co_path: str, config_path: str | None
) -> tuple[int, int, float]:
    """
    Component extraction worker function.
    Running in a separate process to avoid GIL and Segfault issues from C-extensions (fitz).
    """
    if config_path:
        os.environ["MODORA_CONFIG"] = config_path
    
    # Reload settings and configure logging in the worker process
    settings = Settings.load(config_path)
    # Basic logging setup for worker, or we can configure it properly
    # If not configured, logs might be lost or printed to stderr
    # configure_logging(settings) 
    logger = logging.getLogger("modora.preprocess.worker")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)
    
    # Run the async logic in the worker's own event loop
    return asyncio.run(_run_get_components(res_path, co_path, logger))


@dataclass(frozen=True)
class _Job:
    idx: int
    pdf_path: str
    out_dir: str
    res_path: str
    co_path: str


def _pydantic_dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def _parse_ocr_response(obj: Any) -> OcrExtractResponse:
    model_validate = getattr(OcrExtractResponse, "model_validate", None)
    if callable(model_validate):
        return model_validate(obj)
    parse_obj = getattr(OcrExtractResponse, "parse_obj", None)
    if callable(parse_obj):
        return parse_obj(obj)
    return OcrExtractResponse(**obj)


def _ocr_worker_run(pdf_path: str) -> tuple[dict[str, Any], int, float]:
    t0 = time.monotonic()
    ocr_res = ocr_extract_pdf(OCRExtractPdfRequest(file_path=pdf_path))
    payload = _pydantic_dump(ocr_res)
    blocks = payload.get("blocks") if isinstance(payload, dict) else None
    n_blocks = len(blocks) if isinstance(blocks, list) else 0
    return payload, n_blocks, time.monotonic() - t0


async def _run_get_components(
    res_path: str, co_path: str, logger: logging.Logger
) -> tuple[int, int, float]:
    t0 = time.monotonic()
    obj = json.loads(Path(res_path).read_text(encoding="utf-8"))
    ocr_res = _parse_ocr_response(obj)
    blocks_n = len(getattr(ocr_res, "blocks", []) or [])
    co_pack = await get_components_async(ocr_res, logger)
    body_n = len(co_pack.body)
    co_pack.save_json(co_path)
    return blocks_n, body_n, time.monotonic() - t0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "ocr", help="Run OCR+get_component for dataset PDFs"
    )
    p.add_argument(
        "--dataset",
        default="/home/yukai/project/MoDora/datasets/MMDA", 
        help="Path to a PDF file or directory"
    )
    p.add_argument(
        "--cache-dir",
        default="cache_v4",
        help="Cache directory (writes <num>/res.json and <num>/co.json)",
    )
    p.add_argument(
        "--component-workers",
        type=int,
        default=8,
        help="Number of get_component workers (threads)",
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


def _natural_key(s: str) -> list[object]:
    parts = re.split(r"(\d+)", s)
    out: list[object] = []
    for p in parts:
        if p.isdigit():
            out.append(int(p))
        else:
            out.append(p.lower())
    return out


def _iter_pdf_paths(dataset_path: str) -> list[str]:
    p = Path(dataset_path)
    if p.is_file():
        if p.suffix.lower() != ".pdf":
            raise ValueError(
                "dataset must be a .pdf file or a directory containing PDFs"
            )
        return [str(p)]
    if not p.is_dir():
        raise ValueError("dataset must be a .pdf file or a directory containing PDFs")

    out: list[str] = []
    for dirpath, _, filenames in os.walk(str(p)):
        for filename in filenames:
            if filename.lower().endswith(".pdf"):
                out.append(os.path.join(dirpath, filename))
    out.sort(key=_natural_key)
    return out


from modora.core.infra.llm.process import ensure_llm_local_loaded, shutdown_llm_local


def _handle_preprocess_ocr_pipeline(
    args: argparse.Namespace, logger: logging.Logger
) -> int:
    """
    预处理流水线入口：PDF -> OCR (Single Thread) -> Components (Multi Thread)。

    流程：
    1. 扫描 dataset 目录下的 PDF 文件。
    2. 检查 cache 目录，支持断点续传（resume）。
    3. 第一阶段：OCR (单线程/主线程)
       - 依次处理每个 PDF，调用 _ocr_worker_run。
       - OCR 结果保存为 res.json。
    4. 第二阶段：Component Extraction (多线程)
       - OCR 完成后，立即异步提交 component 任务到 ThreadPoolExecutor。
       - 结果保存为 co.json。
    """
    config_path = (getattr(args, "config", None) or "").strip() or None
    if config_path:
        os.environ["MODORA_CONFIG"] = config_path

    # Load Settings and Logging
    settings = Settings.load(config_path)
    configure_logging(settings)

    # Ensure LLM is loaded (for enrichment in get_components)
    ensure_llm_local_loaded(settings, logger)

    try:
        cache_dir = str(getattr(args, "cache_dir", "cache"))
        pdf_paths = _iter_pdf_paths(str(args.dataset))
        if not pdf_paths:
            logger.error(
                "no pdf files found", extra={"task_name": "ocr", "dataset": args.dataset}
            )
            return 2

        os.makedirs(cache_dir, exist_ok=True)

        component_workers = int(getattr(args, "component_workers", 8) or 1)
        resume = bool(getattr(args, "resume", False)) and not bool(
            getattr(args, "overwrite", False)
        )

        jobs: list[_Job] = []
        for i, pdf_path in enumerate(pdf_paths, start=1):
            out_dir = os.path.join(cache_dir, str(i))
            res_path = os.path.join(out_dir, "res.json")
            co_path = os.path.join(out_dir, "co.json")
            jobs.append(
                _Job(
                    idx=i,
                    pdf_path=pdf_path,
                    out_dir=out_dir,
                    res_path=res_path,
                    co_path=co_path,
                )
            )

        total = len(jobs)
        done_count = 0
        failed_count = 0
        skipped_count = 0

        pbar = tqdm(total=total, unit="pdf", dynamic_ncols=True)
        pbar.set_postfix(failed=failed_count, skipped=skipped_count, refresh=False)

        def _tick(is_fail=False, is_skip=False) -> None:
            nonlocal done_count, failed_count, skipped_count
            done_count += 1
            if is_fail:
                failed_count += 1
            if is_skip:
                skipped_count += 1
            pbar.update(1)
            pbar.set_postfix(failed=failed_count, skipped=skipped_count, refresh=False)

        # Load OCR model once (single thread)
        ensure_ocr_model_loaded(settings, logger)

        # 启动异步事件循环
        async def _run_tasks():
            co_tasks: dict[asyncio.Task, _Job] = {}
            
            # 使用 ProcessPoolExecutor 运行组件提取任务，以隔离 fitz/paddle 的崩溃风险
            with futures.ProcessPoolExecutor(max_workers=component_workers) as pool:
                loop = asyncio.get_running_loop()

                async def _bounded_run(job):
                    # 在进程池中执行 worker wrapper
                    return await loop.run_in_executor(
                        pool, 
                        _component_worker_wrapper, 
                        job.res_path, 
                        job.co_path, 
                        config_path
                    )

                def _handle_task_done(t: asyncio.Task):
                    if t not in co_tasks:
                        return
                    job = co_tasks.pop(t)
                    try:
                        t.result()
                        logger.info(
                            "pdf done",
                            extra={
                                "task_name": "get_component",
                                "pdf": job.pdf_path,
                                "res": job.res_path,
                                "co": job.co_path,
                            },
                        )
                        _tick()
                    except futures.process.BrokenProcessPool as e:
                        # 进程池损坏，记录错误但不退出，尝试重启或继续
                        logger.error(
                            "process pool broken, retrying job later or skipping",
                            extra={
                                "task_name": "get_component",
                                "pdf": job.pdf_path,
                                "error": str(e),
                            },
                            exc_info=True
                        )
                        # BrokenProcessPool 意味着整个池子挂了，必须重新初始化
                        # 这里我们只标记失败，让外部循环继续（如果池子能自动恢复的话，但 ProcessPoolExecutor 通常不能）
                        # 实际上 ProcessPoolExecutor 一旦 broken 就无法提交新任务
                        # 简单的做法是记录失败，让用户重试。或者在这里抛出让上层重建池子。
                        # 但为了满足“不影响后续进程”，我们需要确保主程序不 crash。
                        # 这里的异常是在 t.result() 抛出的，如果不捕获会向上传播。
                        # 捕获后，failed_count +1。
                        _tick(is_fail=True)
                        
                        # 关键：记录 failed_pdf_id
                        logger.error(f"FAILED_PDF_ID: {job.idx}", extra={"task_name": "preprocess", "pdf_id": job.idx})

                    except Exception as e:
                        logger.error(
                            "get_component failed",
                            extra={
                                "task_name": "get_component",
                                "pdf": job.pdf_path,
                                "error": str(e),
                            },
                            exc_info=True
                        )
                        _tick(is_fail=True)
                        logger.error(f"FAILED_PDF_ID: {job.idx}", extra={"task_name": "preprocess", "pdf_id": job.idx})

                # OCR 并发控制
                # 即使 OCR 运行在线程池中，由于 GPU 显存限制，也不能无限制并发
                # 使用 Semaphore 限制同时进行的 OCR 任务数
                ocr_sem = asyncio.Semaphore(1)  # 限制 OCR 并发为 1 (单卡串行)

                # ProcessPoolExecutor 可能会因为子进程 crash 而 broken
                # 为了支持恢复，我们可能需要在这里实现一个更复杂的调度逻辑，或者简单地允许失败
                # 由于 ProcessPoolExecutor 是 context manager，一旦 broken 很难在内部重启
                # 但如果只是为了“不影响后续进程”，我们只需要确保异常被捕获即可。
                # 真正的“不影响”意味着即使池子坏了，后续任务也能跑。
                # 实际上，如果池子坏了，必须新建一个池子。
                
                # 简单实现：我们已经捕获了 BrokenProcessPool。
                # 如果要自动重启池子，代码会比较复杂，需要把 ProcessPool 的创建放到循环里。
                # 考虑到用户需求是“记录失败的pdf_id”，当前的异常捕获已经足够让程序继续运行（如果池子没完全坏死）或者优雅退出。
                # 可是 BrokenProcessPool 意味着整个池子不可用了。
                # 因此，如果要继续处理，必须重建池子。
                
                # 下面是一个支持自动重启 ProcessPool 的简化版逻辑：
                # 我们不再使用 with ProcessPoolExecutor，而是手动管理
                
                current_pool = futures.ProcessPoolExecutor(max_workers=component_workers)
                
                # 引入信号量限制并发提交数，防止 ProcessPool 队列积压
                # 这样可以确保任何时候 ProcessPool 中只有 component_workers 个任务在运行或排队
                # 一旦 crash，受影响的任务数也是有限的
                submit_sem = asyncio.Semaphore(component_workers)
                
                # 引入 ProcessPool 重建锁，防止并发任务同时重建
                pool_lock = asyncio.Lock()

                try:
                    for job in jobs:
                        # ... (existing setup code) ...
                        os.makedirs(job.out_dir, exist_ok=True)
                        res_exists = os.path.isfile(job.res_path)
                        co_exists = os.path.isfile(job.co_path)

                        if resume and res_exists and co_exists:
                            logger.info("pdf done (skipped)", extra={"task_name": "get_component", "pdf": job.pdf_path, "res": job.res_path, "co": job.co_path})
                            _tick(is_skip=True)
                            continue

                        need_res = not res_exists or not resume

                        if need_res:
                            # ... (OCR logic) ...
                            try:
                                async with ocr_sem:
                                    loop = asyncio.get_running_loop()
                                    payload, n_blocks, ocr_s = await loop.run_in_executor(
                                        None, _ocr_worker_run, job.pdf_path
                                    )
                                    await loop.run_in_executor(
                                        None,
                                        lambda: Path(job.res_path).write_text(
                                            json.dumps(payload, ensure_ascii=False, indent=2),
                                            encoding="utf-8",
                                        )
                                    )
                            except Exception as e:
                                logger.error("ocr failed", extra={"task_name": "ocr", "pdf": job.pdf_path, "error": str(e)}, exc_info=True)
                                _tick(is_fail=True)
                                logger.error(f"FAILED_PDF_ID: {job.idx}", extra={"task_name": "preprocess", "pdf_id": job.idx})
                                continue

                        # Step 2: Components
                        # 使用信号量控制提交速率
                        await submit_sem.acquire()

                        async def _submit_job(j, retry=0):
                            nonlocal current_pool
                            try:
                                # 在提交前检查池子状态（简单检查）
                                # 如果池子 broken，run_in_executor 会抛出 BrokenProcessPool
                                # 但这里我们无法预知，只能尝试运行
                                async with pool_lock:
                                    if getattr(current_pool, "_broken", False):
                                        logger.warning("ProcessPool broken detected before submit, restarting...", extra={"task_name": "preprocess"})
                                        current_pool.shutdown(wait=False)
                                        current_pool = futures.ProcessPoolExecutor(max_workers=component_workers)
                                    pool = current_pool

                                return await loop.run_in_executor(
                                    pool, 
                                    _component_worker_wrapper, 
                                    j.res_path, 
                                    j.co_path, 
                                    config_path
                                )
                            except futures.process.BrokenProcessPool:
                                # 如果捕获到 BrokenProcessPool，说明池子坏了
                                # 我们需要重建池子并重试（如果是受害者）
                                # 如果重试次数过多，放弃
                                if retry >= 1:
                                    raise # 再次抛出，由外部捕获记录失败
                                
                                logger.warning(f"Job {j.idx} encountered BrokenProcessPool, retrying...", extra={"task_name": "preprocess"})
                                async with pool_lock:
                                    if not getattr(current_pool, "_broken", False):
                                        # 如果别人已经重建了，直接用
                                        pass
                                    else:
                                        # 重建
                                        logger.warning("ProcessPool broken (caught in task), restarting...", extra={"task_name": "preprocess"})
                                        current_pool.shutdown(wait=False)
                                        current_pool = futures.ProcessPoolExecutor(max_workers=component_workers)
                                
                                # 递归重试
                                return await _submit_job(j, retry=retry+1)
                            finally:
                                # 任务完成（无论成功失败），释放信号量，允许下一个任务提交
                                submit_sem.release()

                        task = asyncio.create_task(_submit_job(job))
                        co_tasks[task] = job
                        task.add_done_callback(_handle_task_done)

                    # Wait for all tasks to complete
                    if co_tasks:
                        await asyncio.gather(*co_tasks.keys(), return_exceptions=True)
                finally:
                    current_pool.shutdown(wait=True)

        try:
            asyncio.run(_run_tasks())
        finally:
            pbar.close()

        if failed_count:
            logger.error(
                "preprocess ocr pipeline finished with failures",
                extra={
                    "task_name": "preprocess",
                    "total": total,
                    "failed": failed_count,
                    "cache_dir": cache_dir,
                },
            )
            return 2

        logger.info(
            "preprocess ocr pipeline finished",
            extra={
                "task_name": "preprocess",
                "total": total,
                "failed": 0,
                "cache_dir": cache_dir,
            },
        )
        return 0
    finally:
        shutdown_llm_local()
