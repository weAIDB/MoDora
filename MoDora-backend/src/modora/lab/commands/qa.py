from __future__ import annotations

import argparse
import asyncio
import json
import logging

from modora.core.domain.cctree import CCTree, CCTreeNode
from modora.core.domain.component import Location
from modora.core.services.qa_service import QAService
from modora.core.settings import Settings
from modora.core.infra.llm.process import ensure_llm_local_loaded, shutdown_llm_local
from modora.core.utils.config import (
    load_ui_settings_from_config,
    settings_from_ui_payload,
)


def register(sub: argparse._SubParsersAction) -> None:
    """Register the qa subcommand.

    Args:
        sub: The sub-parsers action to add the parser to.
    """
    parser = sub.add_parser("qa", help="Run QA on a single document")
    parser.add_argument("source_path", help="Path to the original PDF file")
    parser.add_argument("tree_path", help="Path to the tree.json file")
    parser.add_argument("query", help="The question to ask")
    parser.set_defaults(_handler=_handle_qa)


def _handle_qa(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Handler for the qa command.

    Args:
        args: Command line arguments.
        logger: Logger instance.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
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
        asyncio.run(
            run_qa(
                args.source_path,
                args.tree_path,
                args.query,
                qa_settings,
                qa_mode,
                retriever_settings,
                retriever_mode,
                logger,
            )
        )
        return 0
    except Exception as e:
        logger.error(f"QA failed: {e}")
        return 1
    finally:
        shutdown_llm_local()


async def run_qa(
    source_path: str,
    tree_path: str,
    query: str,
    qa_settings: Settings,
    qa_mode: str | None,
    retriever_settings: Settings,
    retriever_mode: str | None,
    logger: logging.Logger,
):
    """Run the QA process for a single document.

    Args:
        source_path: Path to the original PDF file.
        tree_path: Path to the tree.json file.
        query: The question to ask.
        logger: Logger instance.
    """
    qa_service = QAService(
        qa_settings,
        qa_mode=qa_mode,
        retriever_settings=retriever_settings,
        retriever_mode=retriever_mode,
    )

    # Load tree data
    logger.info(f"Loading tree from {tree_path}...")
    try:
        with open(tree_path, "r", encoding="utf-8") as f:
            tree_data = json.load(f)

        def dict_to_node(data):
            """Convert a dictionary to a CCTreeNode object.

            Args:
                data: The dictionary to convert.

            Returns:
                A CCTreeNode object.
            """
            node = CCTreeNode(
                type=data.get("type", "unknown"),
                metadata=data.get("metadata"),
                data=data.get("data", ""),
                location=[Location.from_dict(loc) for loc in data.get("location", [])],
                children={},
            )
            for k, v in data.get("children", {}).items():
                node.children[k] = dict_to_node(v)
            return node

        if "root" in tree_data:  # If wrapped in {root: ...}
            root_node = dict_to_node(tree_data["root"])
        else:  # If it is the original root node
            root_node = dict_to_node(tree_data)

        cctree = CCTree(root=root_node)

    except Exception as e:
        logger.error(f"Failed to load tree: {e}")
        return

    # Execute QA
    logger.info(f"Answering query: {query}")
    result = await qa_service.qa(cctree, query, source_path)

    # Print results and retrieval trace
    print("\n" + "=" * 50)
    print(f"QUESTION: {query}")
    print("-" * 50)

    print("RETRIEVAL TRACE:")
    trace = result.get("retrieval_trace", [])
    for event in trace:
        step = event.get("step")
        if step == "extract_location":
            print(
                f"  [ExtractLoc] Pages: {event.get('page_list')}, Pos: {event.get('position_vector')}"
            )
        elif step == "retrieve":
            print(f"  [Retrieve] Found {event.get('locations_count')} locations")
        elif step == "verification":
            print(f"  [Verify] {event.get('status')}")
        elif step == "fallback":
            print(f"  [Fallback] Reason: {event.get('reason')}")

    print("-" * 50)
    print(f"ANSWER: {result['answer']}")
    print("-" * 50)
    print(f"EVIDENCE (Top {len(result['retrieved_documents'])} snippets):")
    for doc in result["retrieved_documents"]:
        print(f"Page {doc['page']}: {doc['content'][:100]}...")
    print("=" * 50 + "\n")
