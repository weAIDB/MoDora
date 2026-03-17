from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import re
from typing import Any
from tqdm import tqdm

from modora.core.domain.component import ComponentPack
from modora.core.preprocess import build_tree_async
from modora.core.domain.jobs import BuildTreeJob
from modora.core.settings import Settings
from modora.core.infra.llm import ensure_llm_local_loaded, shutdown_llm_local
from modora.core.utils import iter_pdf_paths


def register(sub: argparse._SubParsersAction) -> None:
    """Register the build-tree subcommand.

    Args:
        sub: The sub-parsers action to add the parser to.
    """
    p = sub.add_parser("build-tree", help="Build title.json and tree.json for dataset")
    p.add_argument(
        "--dataset",
        default=None,
        help="Path to a directory containing <num>.pdf files",
    )
    p.add_argument(
        "--cache-dir",
        default=None,
        help="Cache directory containing <num>/co.json",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=16,
        help="Max concurrent PDFs (0=auto)",
    )
    p.add_argument(
        "--filter-list",
        help="Path to a file containing a list of PDF filenames to process (one per line)",
    )
    p.set_defaults(_handler=_handle_build_tree)


def _resolve_concurrency(args: argparse.Namespace, settings: Settings) -> int:
    """Resolve the concurrency level.

    If not specified, the concurrency level is determined by the number of local
    LLM instances.

    Args:
        args: Command-line arguments.
        settings: Application settings.

    Returns:
        The resolved concurrency level.
    """
    concurrency = int(getattr(args, "concurrency", 0) or 0)
    if concurrency <= 0:
        inst = list(getattr(settings, "llm_local_instances", ()) or ())
        concurrency = max(1, len(inst) or 1)
    return concurrency


def _build_jobs(
    pdf_paths: list[Path], cache_dir: Path, logger: logging.Logger, pbar: Any
) -> tuple[list[BuildTreeJob], int]:
    """Build a list of jobs based on PDF paths and verify the existence of co.json.

    Args:
        pdf_paths: List of paths to the PDF files.
        cache_dir: Directory containing the cache files.
        logger: Logger instance for error reporting.
        pbar: Progress bar instance.

    Returns:
        A tuple containing the list of jobs and the number of failed jobs.
    """
    jobs: list[BuildTreeJob] = []
    failed = 0
    for pdf_path in pdf_paths:
        m = re.fullmatch(r"(\d+)", pdf_path.stem)
        if not m:
            pbar.update(1)
            continue

        num = int(m.group(1))
        co_path = cache_dir / str(num) / "co.json"
        out_dir = co_path.parent
        title_path = out_dir / "title.json"
        tree_path = out_dir / "tree.json"

        if not co_path.is_file():
            logger.error(
                "co.json not found",
                extra={"num": num, "pdf": str(pdf_path), "co": str(co_path)},
            )
            failed += 1
            pbar.update(1)
            continue

        jobs.append(
            BuildTreeJob(
                num=num,
                pdf_path=pdf_path,
                co_path=co_path,
                out_dir=out_dir,
                title_path=title_path,
                tree_path=tree_path,
            )
        )
    return jobs, failed


async def _run_one_job(
    job: BuildTreeJob, sem: asyncio.Semaphore, logger: logging.Logger
) -> bool:
    """Run a single build-tree job.

    Loads co.json, builds the tree, extracts titles, and saves the results.

    Args:
        job: The build-tree job to run.
        sem: Semaphore for concurrency control.
        logger: Logger instance for logging events.

    Returns:
        True if the job completed successfully, False otherwise.
    """
    async with sem:
        try:
            cp = await asyncio.to_thread(ComponentPack.load_json, str(job.co_path))
            source = f"file:{str(job.pdf_path)}"
            tree = await build_tree_async(cp, logger, source)

            # Extract and format title information
            titles: list[dict[str, Any]] = []
            for co in cp.body:
                if co.type != "text":
                    continue
                level = int(getattr(co, "title_level", 1) or 1)
                leveled = ("#" * level + " " + co.title).strip()
                titles.append(
                    {
                        "title": co.title,
                        "title_level": level,
                        "leveled_title": leveled,
                    }
                )

            payload = {"source": source, "titles": titles}
            # Ensure output directory exists
            await asyncio.to_thread(os.makedirs, job.out_dir, exist_ok=True)
            # Save title information
            await asyncio.to_thread(
                job.title_path.write_text,
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                "utf-8",
            )
            # Save tree structure
            await asyncio.to_thread(tree.save_json, str(job.tree_path))
            return True
        except Exception as e:
            logger.exception(
                "build_tree failed",
                extra={
                    "num": job.num,
                    "pdf": str(job.pdf_path),
                    "co": str(job.co_path),
                    "title": str(job.title_path),
                    "tree": str(job.tree_path),
                    "error": str(e),
                },
            )
            return False


async def _run_jobs(
    jobs: list[BuildTreeJob], concurrency: int, logger: logging.Logger, pbar: Any
) -> tuple[int, int]:
    """Run build jobs in batches.

    Args:
        jobs: List of jobs to run.
        concurrency: Number of concurrent jobs.
        logger: Logger instance.
        pbar: Progress bar instance.

    Returns:
        A tuple containing the number of successful and failed jobs.
    """
    sem = asyncio.Semaphore(concurrency)
    tasks = [asyncio.create_task(_run_one_job(job, sem, logger)) for job in jobs]
    ok = 0
    failed = 0
    for t in asyncio.as_completed(tasks):
        if await t:
            ok += 1
        else:
            failed += 1
        pbar.update(1)
    return ok, failed


def _handle_build_tree(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Handler for the build-tree command.

    Args:
        args: Command-line arguments.
        logger: Logger instance.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    config_path = (getattr(args, "config", None) or "").strip() or None
    if config_path:
        os.environ["MODORA_CONFIG"] = config_path

    settings = Settings.load(config_path)
    ensure_llm_local_loaded(settings, logger)

    try:
        dataset_value = str(getattr(args, "dataset", "") or "").strip()
        cache_value = str(getattr(args, "cache_dir", "") or "").strip()
        dataset_dir = Path(
            dataset_value or (settings.docs_dir or "")
        ).resolve()
        cache_dir = Path(
            cache_value or (settings.cache_dir or "")
        ).resolve()

        pdf_paths = list(iter_pdf_paths(dataset_dir))

        # Apply whitelist filtering
        filter_list_path = (getattr(args, "filter_list", None) or "").strip()
        if filter_list_path:
            filter_path = Path(filter_list_path).resolve()
            if filter_path.is_file():
                whitelist = {
                    line.strip()
                    for line in filter_path.read_text("utf-8").splitlines()
                    if line.strip()
                }
                pdf_paths = [
                    p for p in pdf_paths if p.name in whitelist or p.stem in whitelist
                ]
                logger.info(f"Filtered to {len(pdf_paths)} PDFs from whitelist")
            else:
                logger.warning(f"Filter list file not found: {filter_path}")

        total = len(pdf_paths)
        ok = 0
        failed = 0

        concurrency = _resolve_concurrency(args, settings)

        pbar = tqdm(total=total, unit="pdf", dynamic_ncols=True)
        try:
            jobs, failed_jobs = _build_jobs(pdf_paths, cache_dir, logger, pbar)
            failed += failed_jobs

            if jobs:
                local_ok, local_failed = asyncio.run(
                    _run_jobs(jobs, concurrency, logger, pbar)
                )
                ok += local_ok
                failed += local_failed
        finally:
            pbar.close()

        report = {"total": total, "ok": ok, "failed": failed}
        if failed:
            logger.error("build-tree finished with failures", extra=report)
            return 2
        logger.info("build-tree finished", extra=report)
        return 0
    finally:
        shutdown_llm_local()
