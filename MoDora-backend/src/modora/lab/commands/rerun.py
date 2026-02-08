import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import List

from modora.core.settings import Settings
from modora.lab.commands.batch_qa import QAJob, resolve_paths, run_batch_qa
from modora.core.infra.llm.process import ensure_llm_local_loaded, shutdown_llm_local


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("rerun", help="Rerun failed QA tasks from evaluation results")
    parser.add_argument(
        "--eval-file",
        required=True,
        help="Path to the evaluation result file (jsonl)",
    )
    parser.add_argument(
        "--dataset",
        default="/home/yukai/project/MoDora/datasets/MMDA/test.json",
        help="Path to the dataset JSON file (e.g., test.json)",
    )
    parser.add_argument(
        "--cache-dir",
        default="/home/yukai/project/MoDora/MoDora-backend/cache_v4",
        help="Path to the cache directory containing trees",
    )
    parser.add_argument(
        "--output-dir",
        default="/home/yukai/project/MoDora/MoDora-backend/tmp/rerun",
        help="Directory to save intermediate and final results",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent QA tasks",
    )
    parser.set_defaults(_handler=_handle_rerun)


def _handle_rerun(args: argparse.Namespace, logger: logging.Logger) -> int:
    settings = Settings.load()
    ensure_llm_local_loaded(settings, logger)

    try:
        eval_path = Path(args.eval_file).resolve()
        dataset_path = Path(args.dataset).resolve()
        cache_dir = Path(args.cache_dir).resolve()
        output_dir = Path(args.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Identify failed question IDs
        failed_ids = set()
        with open(eval_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if item.get("judge") == "F":
                        failed_ids.add(item.get("questionId"))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON line: {line}")

        if not failed_ids:
            logger.info("No failed cases found (judge='F'). Exiting.")
            return 0
        
        logger.info(f"Found {len(failed_ids)} failed cases to rerun.")

        # 2. Load dataset and filter jobs
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        jobs: List[QAJob] = []
        for item in dataset:
            if item.get("questionId") in failed_ids:
                job = resolve_paths(item, dataset_path, cache_dir, output_dir)
                if job:
                    jobs.append(job)
        
        logger.info(f"Prepared {len(jobs)} QA jobs for rerun.")

        if not jobs:
            logger.warning("No matching jobs found in dataset for the failed IDs.")
            return 0

        # 3. Run Batch QA
        results = asyncio.run(run_batch_qa(jobs, args.concurrency, logger))

        # 4. Save results
        final_output_path = output_dir / "rerun_result.json"
        with open(final_output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"Rerun finished. Results saved to {final_output_path}")
        return 0

    except Exception as e:
        logger.error(f"Rerun failed: {e}")
        return 1
    finally:
        shutdown_llm_local()
