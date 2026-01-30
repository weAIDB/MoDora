import argparse
import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from tqdm import tqdm

from modora.core.domain.cctree import CCTree, CCTreeNode
from modora.core.domain.component import Location
from modora.core.services.qa import QAService
from modora.core.settings import Settings
from modora.service.api.llm_local import ensure_llm_local_loaded, shutdown_llm_local


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("batch-qa", help="Run batch QA experiments")
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
        default="/home/yukai/project/MoDora/MoDora-backend/tmp",
        help="Directory to save intermediate and final results",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent QA tasks",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit the number of QA tasks to run (0 for all)",
    )
    parser.set_defaults(_handler=_handle_batch_qa)


@dataclass
class QAJob:
    question_id: int
    question: str
    pdf_path: Path
    tree_path: Path
    answer: str  # Ground truth
    output_path: Path


def _resolve_paths(
    item: dict[str, Any], dataset_json_path: Path, cache_dir: Path, output_dir: Path
) -> QAJob | None:
    try:
        pdf_filename = item["pdf_id"]
        pdf_num = pdf_filename.replace(".pdf", "")
        
        # PDF Path: assume dataset directory structure is consistent
        # /path/to/MMDA/test.json -> /path/to/MMDA/1.pdf
        pdf_path = dataset_json_path.parent / pdf_filename
        
        # Tree Path: cache_dir/<num>/tree.json
        tree_path = cache_dir / pdf_num / "tree.json"
        
        # Output Path
        output_path = output_dir / f"qa_{item['questionId']}_result.json"
        
        if not pdf_path.exists():
            logging.warning(f"PDF not found: {pdf_path}")
            return None
        if not tree_path.exists():
            logging.warning(f"Tree not found: {tree_path}")
            return None
            
        return QAJob(
            question_id=item["questionId"],
            question=item["question"],
            pdf_path=pdf_path,
            tree_path=tree_path,
            answer=item["answer"],
            output_path=output_path,
        )
    except Exception as e:
        logging.error(f"Error resolving paths for item {item}: {e}")
        return None


async def _run_single_qa(
    job: QAJob, qa_service: QAService, sem: asyncio.Semaphore, logger: logging.Logger
) -> dict[str, Any] | None:
    async with sem:
        try:
            # Load Tree
            with open(job.tree_path, "r", encoding="utf-8") as f:
                tree_data = json.load(f)

            def dict_to_node(data):
                node = CCTreeNode(
                    type=data.get("type", "unknown"),
                    metadata=data.get("metadata"),
                    data=data.get("data", ""),
                    location=[Location.from_dict(l) for l in data.get("location", [])],
                    children={},
                )
                for k, v in data.get("children", {}).items():
                    node.children[k] = dict_to_node(v)
                return node

            if "root" in tree_data:
                root_node = dict_to_node(tree_data["root"])
            else:
                root_node = dict_to_node(tree_data)
            
            cctree = CCTree(root=root_node)

            # Run QA
            result = await qa_service.answer_question(
                job.question, cctree, str(job.pdf_path), job.question_id
            )
            
            output = {
                "questionId": job.question_id,
                "question": job.question,
                "ground_truth": job.answer,
                "prediction": result["answer"],
                "evidence": result["retrieved_documents"],
                "status": "success"
            }
            
            # Save intermediate result
            with open(job.output_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
                
            return output

        except Exception as e:
            logger.error(f"QA failed for Question {job.question_id}: {e}")
            return {
                "questionId": job.question_id,
                "status": "failed",
                "error": str(e)
            }


async def _run_batch_qa(
    jobs: List[QAJob], concurrency: int, logger: logging.Logger
) -> List[dict[str, Any]]:
    settings = Settings.load()
    qa_service = QAService(settings, logger)
    sem = asyncio.Semaphore(concurrency)
    
    tasks = [
        _run_single_qa(job, qa_service, sem, logger) for job in jobs
    ]
    
    results = []
    for f in tqdm(asyncio.as_completed(tasks), total=len(jobs), desc="Running QA"):
        res = await f
        if res:
            results.append(res)
            
    return results


def _handle_batch_qa(args: argparse.Namespace, logger: logging.Logger) -> int:
    settings = Settings.load()
    ensure_llm_local_loaded(settings, logger)
    
    try:
        dataset_path = Path(args.dataset).resolve()
        cache_dir = Path(args.cache_dir).resolve()
        output_dir = Path(args.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        jobs = []
        for item in dataset:
            job = _resolve_paths(item, dataset_path, cache_dir, output_dir)
            if job:
                jobs.append(job)
        
        # Apply limit if specified
        if args.limit > 0:
            logger.info(f"Limiting to first {args.limit} tasks")
            jobs = jobs[:args.limit]
            
        logger.info(f"Found {len(jobs)} QA jobs")
        
        results = asyncio.run(_run_batch_qa(jobs, args.concurrency, logger))
        
        # Save final summary
        final_output_path = output_dir / "result.json"
        with open(final_output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Batch QA finished. Results saved to {final_output_path}")
        return 0
        
    except Exception as e:
        logger.error(f"Batch QA failed: {e}")
        return 1
    finally:
        shutdown_llm_local()
