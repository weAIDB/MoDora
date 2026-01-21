from __future__ import annotations

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

from modora.core.preprocess import get_components
from modora.core.settings import Settings
from modora.core.domain.ocr import OcrExtractResponse
from modora.service.api.ocr.router import (
    OCRExtractPdfRequest,
    ocr_extract_pdf,
)
from modora.service.api.ocr.runtime import ensure_ocr_model_loaded
from modora.core.infra.logging.setup import configure_logging


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


def _run_get_components(
    res_path: str, co_path: str, logger: logging.Logger
) -> tuple[int, int, float]:
    t0 = time.monotonic()
    obj = json.loads(Path(res_path).read_text(encoding="utf-8"))
    ocr_res = _parse_ocr_response(obj)
    blocks_n = len(getattr(ocr_res, "blocks", []) or [])
    co_pack = get_components(ocr_res, logger)
    body_n = len(co_pack.body)
    co_pack.save_json(co_path)
    return blocks_n, body_n, time.monotonic() - t0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "preprocess-ocr-pipeline", help="Run OCR+get_component for dataset PDFs"
    )
    p.add_argument("--dataset", required=True, help="Path to a PDF file or directory")
    p.add_argument(
        "--cache-dir",
        default="cache",
        help="Cache directory (writes <num>/res.json and <num>/co.json)",
    )
    p.add_argument(
        "--component-workers",
        type=int,
        default=32,
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

    cache_dir = str(getattr(args, "cache_dir", "cache"))
    pdf_paths = _iter_pdf_paths(str(args.dataset))
    if not pdf_paths:
        logger.error("no pdf files found", extra={"taskName": "ocr", "dataset": args.dataset})
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
    settings = Settings.load(config_path)
    configure_logging(settings)
    ensure_ocr_model_loaded(settings, logger)

    co_exec = futures.ThreadPoolExecutor(max_workers=component_workers)
    co_futs: dict[futures.Future[tuple[int, int, float]], _Job] = {}

    def _handle_future_done(f: futures.Future) -> None:
        if f not in co_futs:
            return
        job = co_futs.pop(f)
        try:
            f.result()
            logger.info(
                "pdf done",
                extra={
                    "taskName": "get_component",
                    "pdf": job.pdf_path,
                    "res": job.res_path,
                    "co": job.co_path,
                },
            )
            _tick()
        except Exception as e:
            logger.exception(
                "get_component failed",
                extra={"taskName": "get_component", "pdf": job.pdf_path, "error": str(e)},
            )
            _tick(is_fail=True)

    try:
        for job in jobs:
            os.makedirs(job.out_dir, exist_ok=True)
            res_exists = os.path.isfile(job.res_path)
            co_exists = os.path.isfile(job.co_path)

            if resume and res_exists and co_exists:
                logger.info(
                    "pdf done (skipped)",
                    extra={
                        "i": job.idx,
                        "pdf": job.pdf_path,
                        "res": job.res_path,
                        "co": job.co_path,
                    },
                )
                _tick(is_skip=True)
                continue

            need_res = not res_exists or not resume
            
            # Step 1: OCR (Synchronous)
            if need_res:
                try:
                    payload, n_blocks, ocr_s = _ocr_worker_run(job.pdf_path)
                    Path(job.res_path).write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception as e:
                    logger.exception(
                        "ocr failed",
                        extra={"taskName": "ocr", "pdf": job.pdf_path, "error": str(e)},
                    )
                    _tick(is_fail=True)
                    continue

            # Step 2: Components (Asynchronous)
            fut = co_exec.submit(_run_get_components, job.res_path, job.co_path, logger)
            co_futs[fut] = job

            # Check completed futures (non-blocking)
            if co_futs:
                done_set, _ = futures.wait(
                    list(co_futs.keys()),
                    timeout=0,
                    return_when=futures.FIRST_COMPLETED,
                )
                for f in done_set:
                    _handle_future_done(f)

        # Wait for remaining tasks
        while co_futs:
            done_set, _ = futures.wait(
                list(co_futs.keys()),
                return_when=futures.FIRST_COMPLETED,
            )
            for f in done_set:
                _handle_future_done(f)

    finally:
        co_exec.shutdown(wait=True, cancel_futures=False)
        pbar.close()

    if failed_count:
        logger.error(
            "preprocess ocr pipeline finished with failures",
            extra={"taskName": "preprocess", "total": total, "failed": failed_count, "cache_dir": cache_dir},
        )
        return 2

    logger.info(
        "preprocess ocr pipeline finished",
        extra={"taskName": "preprocess", "total": total, "failed": 0, "cache_dir": cache_dir},
    )
    return 0
