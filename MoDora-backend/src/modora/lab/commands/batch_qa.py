import argparse
import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Any, List

from tqdm import tqdm

from modora.core.domain.cctree import CCTree, CCTreeNode
from modora.core.domain.component import Location
from modora.core.domain.jobs import QAJob
from modora.core.services.qa_service import QAService
from modora.core.settings import Settings
from modora.core.infra.llm.process import ensure_llm_local_loaded, shutdown_llm_local
from modora.core.utils.config import (
    load_ui_settings_from_config,
    settings_from_ui_payload,
)


def register(sub: argparse._SubParsersAction) -> None:
    """Register the batch-qa sub-command."""
    parser = sub.add_parser("batch-qa", help="Run batch QA experiments")
    parser.add_argument(
        "--dataset",
        default="/home/yukai/project/MoDora/datasets/MMDA/test.json",
        help="Path to the dataset JSON file (e.g., test.json)",
    )
    parser.add_argument(
        "--cache",
        default="/home/yukai/project/MoDora/MoDora-backend/cache_v5",
        help="Path to the cache directory containing trees",
    )
    parser.add_argument(
        "--output",
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
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Filter questions by tag (comma-separated, e.g. 1-2,2-2)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (save prompts and images)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing result.json in output directory",
    )
    parser.set_defaults(_handler=_handle_batch_qa)


def resolve_paths(
    item: dict[str, Any], dataset_json_path: Path, cache_dir: Path, output_dir: Path
) -> QAJob | None:
    """Parse and validate the path of each item in the dataset, converting it into a QAJob object."""
    try:
        pdf_filename = item["pdf_id"]
        pdf_num = pdf_filename.replace(".pdf", "")

        # PDF path: assume the dataset directory structure is consistent
        # /path/to/MMDA/test.json -> /path/to/MMDA/1.pdf
        pdf_path = dataset_json_path.parent / pdf_filename

        # Tree path: cache_dir/<num>/tree.json
        tree_path = cache_dir / pdf_num / "tree.json"

        # Output path
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


async def run_single_qa(
    job: QAJob,
    qa_service: QAService,
    sem: asyncio.Semaphore,
    logger: logging.Logger,
    debug: bool = False,
) -> dict[str, Any] | None:
    """Execute a single QA task, including loading the tree, calling the QA service, and saving the results."""
    async with sem:
        try:
            # Load tree data
            with open(job.tree_path, "r", encoding="utf-8") as f:
                tree_data = json.load(f)

            def dict_to_node(data):
                """Convert a dictionary into a CCTreeNode object."""
                node = CCTreeNode(
                    type=data.get("type", "unknown"),
                    metadata=data.get("metadata"),
                    data=data.get("data", ""),
                    location=[
                        Location.from_dict(loc) for loc in data.get("location", [])
                    ],
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

            # Execute QA
            result = await qa_service.qa(cctree, job.question, str(job.pdf_path))

            output = {
                "questionId": job.question_id,
                "question": job.question,
                "ground_truth": job.answer,
                "prediction": result["answer"],
                "evidence": result.get("retrieved_documents", []),
                "status": "success",
            }

            # Save intermediate results
            with open(job.output_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            # Save prompts and images in debug mode
            if debug:
                try:
                    debug_dir = job.output_path.parent / "debug" / str(job.question_id)
                    debug_dir.mkdir(parents=True, exist_ok=True)

                    debug_prompts = result.get("debug_prompts", {})

                    # Save inference context
                    with open(debug_dir / "prompt.txt", "w", encoding="utf-8") as f:
                        f.write(debug_prompts.get("reasoning_context", ""))

                    # Save fallback context
                    if debug_prompts.get("fallback_context"):
                        with open(
                            debug_dir / "fallback_prompt.txt", "w", encoding="utf-8"
                        ) as f:
                            f.write(debug_prompts.get("fallback_context", ""))

                    # Save images
                    images = debug_prompts.get("images", [])
                    for i, img_b64 in enumerate(images):
                        try:
                            img_data = base64.b64decode(img_b64)
                            with open(debug_dir / f"image_{i}.jpg", "wb") as f:
                                f.write(img_data)
                        except Exception as e:
                            logger.error(f"Failed to save debug image {i}: {e}")

                except Exception as e:
                    logger.error(
                        f"Failed to save debug info for Question {job.question_id}: {e}"
                    )

            return output

        except Exception as e:
            logger.error(f"QA failed for Question {job.question_id}: {e}")
            return {"questionId": job.question_id, "status": "failed", "error": str(e)}


async def run_batch_qa(
    jobs: List[QAJob],
    qa_service: QAService,
    concurrency: int,
    logger: logging.Logger,
    debug: bool = False,
) -> List[dict[str, Any]]:
    """Run QA tasks in batch."""
    sem = asyncio.Semaphore(concurrency)

    tasks = [run_single_qa(job, qa_service, sem, logger, debug) for job in jobs]

    results = []
    for f in tqdm(asyncio.as_completed(tasks), total=len(jobs), desc="Running QA"):
        res = await f
        if res:
            results.append(res)

    return results


def _handle_batch_qa(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Processor for the batch-qa command."""
    config_path = getattr(args, "config", None)
    settings = Settings.load(config_path)
    ensure_llm_local_loaded(settings, logger, config_path=config_path)

    try:
        ui_settings = load_ui_settings_from_config(config_path)
        qa_settings, qa_mode, cfg = settings_from_ui_payload(
            settings, ui_settings, module_key="qaService"
        )
        retriever_settings, retriever_mode, _ = settings_from_ui_payload(
            settings, cfg, module_key="retriever"
        )
        qa_service = QAService(
            qa_settings,
            qa_mode=qa_mode,
            retriever_settings=retriever_settings,
            retriever_mode=retriever_mode,
        )

        dataset_path = Path(args.dataset).resolve()
        cache_dir = Path(args.cache).resolve()
        output_dir = Path(args.output).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        # Filter by tags if specified
        if args.tag:
            target_tags = set(t.strip() for t in args.tag.split(","))
            logger.info(f"Filtering by tags: {target_tags}")
            dataset = [item for item in dataset if item.get("tag") in target_tags]

        jobs = []
        for item in dataset:
            job = resolve_paths(item, dataset_path, cache_dir, output_dir)
            if job:
                jobs.append(job)

        # Limit the number of tasks if specified
        if args.limit > 0:
            logger.info(f"Limiting to first {args.limit} tasks")
            jobs = jobs[: args.limit]

        # Resume logic: skip successfully processed questions
        existing_results = []
        final_output_path = output_dir / "result.json"
        if args.resume and final_output_path.exists():
            try:
                with open(final_output_path, "r", encoding="utf-8") as f:
                    resume_data = json.load(f)

                if isinstance(resume_data, dict) and "results" in resume_data:
                    existing_results = resume_data["results"]
                elif isinstance(resume_data, list):
                    existing_results = resume_data
                else:
                    logger.warning(
                        f"Existing results in {final_output_path} has unknown format, ignoring for resume"
                    )
                    existing_results = []

                processed_ids = {
                    res["questionId"]
                    for res in existing_results
                    if isinstance(res, dict) and res.get("status") == "success"
                }
                logger.info(
                    f"Resuming: found {len(processed_ids)} already processed tasks in {final_output_path}"
                )

                original_count = len(jobs)
                jobs = [j for j in jobs if j.question_id not in processed_ids]
                logger.info(f"Filtered tasks: {original_count} -> {len(jobs)}")
            except Exception as e:
                logger.error(f"Failed to load existing results for resume: {e}")

        logger.info(f"Found {len(jobs)} QA jobs to run")

        new_results = []
        if jobs:
            new_results = asyncio.run(
                run_batch_qa(jobs, qa_service, args.concurrency, logger, args.debug)
            )

        # Merge and save final summary
        all_results = existing_results + new_results

        # Deduplicate by questionId, keeping the latest result
        results_map = {
            res["questionId"]: res for res in all_results if "questionId" in res
        }
        final_results = sorted(results_map.values(), key=lambda x: x["questionId"])

        # Construct final output, trying to preserve existing metrics
        if (
            args.resume
            and "resume_data" in locals()
            and isinstance(resume_data, dict)
            and "metrics" in resume_data
        ):
            final_output = {"metrics": resume_data["metrics"], "results": final_results}
        else:
            final_output = final_results

        with open(final_output_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Batch QA finished. Total {len(final_results)} results saved to {final_output_path}"
        )
        return 0

    except Exception as e:
        logger.error(f"Batch QA failed: {e}")
        return 1
    finally:
        shutdown_llm_local()
