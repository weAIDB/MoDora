import json
import logging
import asyncio
import argparse
import shutil
from pathlib import Path
from typing import Any
from modora.core.settings import Settings
from modora.core.infra.llm.process import ensure_llm_local_loaded, shutdown_llm_local
from modora.core.services.qa_service import QAService
from modora.core.services.retrieve import SemanticRetriever, LocationRetriever
from modora.core.domain.cctree import CCTree, CCTreeNode
from modora.core.domain.component import Location
from modora.core.infra.llm.factory import AsyncLLMFactory
from modora.core.infra.pdf.cropper import PDFCropper

def load_cctree(tree_path):
    with open(tree_path, "r", encoding="utf-8") as f:
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
    
    return CCTree(root=root_node)


class LocalQAService(QAService):
    """
    Override QAService to force using local LLM for all operations.
    """
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.local_llm = AsyncLLMFactory.create(settings, mode="local")
        self.remote_llm = AsyncLLMFactory.create(settings, mode="local")
        self.cropper = PDFCropper()
        self.semantic_retriever = SemanticRetriever(self.settings)
        self.location_retriever = LocationRetriever()

async def process_single_case(
    sem: asyncio.Semaphore,
    case: dict,
    qa_service: QAService,
    badcase_dir: Path,
    pdf_base_path: Path,
    tree_base_path: Path
):
    async with sem:
        qid = case.get("questionId")
        pdf_id = case.get("pdf_id")
        query = case.get("question")
        
        # Construct paths
        pdf_id_clean = str(pdf_id).replace(".pdf", "")
        # Assuming standard structure: cache_v4/{pdf_id}/tree.json
        tree_path = tree_base_path / pdf_id_clean / "tree.json"
        source_path = pdf_base_path / pdf_id
        
        output_file = badcase_dir / f"{qid}.txt"

        content_buffer = []
        
        content_buffer.append(f"QID: {qid} | PDF: {pdf_id}")
        content_buffer.append(f"QUESTION: {query}")
        content_buffer.append("-" * 80)
        content_buffer.append(f"PREVIOUS PREDICTION: {case.get('prediction')}")
        content_buffer.append(f"EXPECTED ANSWER: {case.get('answer')}")
        content_buffer.append("-" * 80)

        if not tree_path.exists():
            content_buffer.append(f"SKIP: Tree file not found at {tree_path}")
            await _write_file(output_file, "\n".join(content_buffer))
            return
            
        if not source_path.exists():
            content_buffer.append(f"SKIP: Source PDF not found at {source_path}")
            await _write_file(output_file, "\n".join(content_buffer))
            return

        try:
            # Load tree
            cctree = await asyncio.to_thread(load_cctree, tree_path)
            
            result = await qa_service.qa(cctree, query, str(source_path))
            
            content_buffer.append("RETRIEVAL TRACE:")
            trace = result.get("retrieval_trace", [])
            for event in trace:
                step = event.get("step")
                if step == "extract_location":
                    content_buffer.append(f"  [ExtractLoc] Pages: {event.get('page_list')}, Pos: {event.get('position_vector')}")
                elif step == "retrieve":
                    content_buffer.append(f"  [Retrieve] Found {event.get('locations_count')} locations")
                elif step == "verification":
                    content_buffer.append(f"  [Verify] {event.get('status')}")
                elif step == "fallback":
                    content_buffer.append(f"  [Fallback] Reason: {event.get('reason')}")
            
            content_buffer.append("-" * 80)
            content_buffer.append(f"NEW ANSWER: {result['answer']}")
            content_buffer.append("-" * 80)
            
            content_buffer.append(f"EVIDENCE (Top {len(result['retrieved_documents'])} snippets):")
            for doc in result["retrieved_documents"]:
                content_preview = doc['content'][:200].replace('\n', ' ')
                content_buffer.append(f"Page {doc['page']}: {content_preview}...")
            
        except Exception as e:
            content_buffer.append(f"ERROR: {e}")
            print(f"Error processing QID {qid}: {e}")

        await _write_file(output_file, "\n".join(content_buffer))
        print(f"Finished QID: {qid}")

async def _write_file(path: Path, content: str):
    async with asyncio.Lock(): # Simple lock if needed, though separate files usually safe
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

async def main():
    parser = argparse.ArgumentParser(description="Run Bad Case Analysis")
    parser.add_argument("--eval-file", type=str, required=True, help="Path to eval.jsonl")
    parser.add_argument("--pdf-dir", type=str, default="/home/yukai/project/MoDora/datasets/MMDA", help="Base directory for PDFs")
    parser.add_argument("--tree-dir", type=str, default="/home/yukai/project/MoDora/MoDora-backend/cache_v4", help="Base directory for tree caches")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent tasks")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of bad cases to process")
    args = parser.parse_args()

    eval_path = Path(args.eval_file)
    if not eval_path.exists():
        print(f"Error: Evaluation file not found at {eval_path}")
        return

    # Create badcase directory under the same parent as eval file
    badcase_dir = eval_path.parent / "badcase"
    if badcase_dir.exists():
        shutil.rmtree(badcase_dir)
    badcase_dir.mkdir(parents=True, exist_ok=True)
    print(f"Bad cases will be saved to: {badcase_dir}")

    bad_cases = []
    with open(eval_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if data.get("judge", "F") == "F":
                    bad_cases.append(data)
            except json.JSONDecodeError:
                continue

    bad_cases.sort(key=lambda x: x.get('questionId', 0))
    if args.limit:
        bad_cases = bad_cases[:args.limit]
    print(f"Found {len(bad_cases)} bad cases (limit: {args.limit}).")

    settings = Settings.load()
    logger = logging.getLogger("modora.badcase")
    logger.setLevel(logging.WARNING) 
    
    ensure_llm_local_loaded(settings, logger)
    
    try:
        # Use LocalQAService which forces local LLM
        qa_service = LocalQAService(settings, logger)
        
        sem = asyncio.Semaphore(args.concurrency)
        tasks = []
        
        pdf_base_path = Path(args.pdf_dir)
        tree_base_path = Path(args.tree_dir)

        for case in bad_cases:
            tasks.append(
                process_single_case(
                    sem, case, qa_service, badcase_dir, pdf_base_path, tree_base_path
                )
            )
        
        await asyncio.gather(*tasks)
        print("All tasks completed.")

    finally:
        shutdown_llm_local()

if __name__ == "__main__":
    asyncio.run(main())
