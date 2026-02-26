from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from modora.core.domain.cctree import CCTree
from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths
from modora.core.utils.config import settings_from_ui_payload
from modora.core.services.qa_service import QAService
from modora.api.v1.models import ChatRequest, ChatResponse, RetrievalItem

router = APIRouter(tags=["chat"])
logger = logging.getLogger("modora.api")


def _settings_from_payload(
    payload: dict[str, Any] | None,
) -> tuple[Settings, str | None, Settings, str | None]:
    settings = Settings.load()
    qa_settings, _, qa_instance, cfg = settings_from_ui_payload(
        settings, payload, module_key="qaService"
    )
    retriever_settings, _, retriever_instance, _ = settings_from_ui_payload(
        settings, cfg, module_key="retriever"
    )
    return (
        qa_settings,
        qa_instance,
        retriever_settings,
        retriever_instance,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    settings_payload = request.settings or {}
    file_names = request.file_names or (
        [] if not request.file_name else [request.file_name]
    )
   
    if not file_names:
        raise HTTPException(status_code=400, detail="File name(s) required")

    (
        app_settings,
        qa_instance,
        retriever_settings,
        retriever_instance,
    ) = _settings_from_payload(settings_payload)
    paths = resolve_paths(app_settings)

    # Load tree structures for all documents
    trees: dict[str, CCTree] = {}
    source_paths: dict[str, str] = {}

    for fn in file_names:
        s_path = paths.docs_dir / fn
        if not s_path.exists():
            continue

        t_path = paths.doc_cache_dir(fn) / "tree.json"
        if not t_path.exists():
            continue

        try:
            t_dict = json.loads(t_path.read_text(encoding="utf-8"))
            trees[fn] = CCTree.from_dict(t_dict)
            source_paths[fn] = str(s_path)
        except Exception as e:
            logger.warning(f"Failed to load tree for {fn}: {e}")

    if not trees:
        raise HTTPException(status_code=404, detail="No valid document trees found.")

    # Decide between single or multi-document based on the number of documents
    if len(trees) > 1:
        # Multi-document: Merge trees
        cctree = CCTree.merge_multi_trees(trees)
        source_arg = source_paths
        primary = "multi_doc_session"  # For identification only
    else:
        # Single document: Keep as is
        primary = list(trees.keys())[0]
        cctree = trees[primary]
        source_arg = source_paths[primary]

    # Use the core QAService with the overrides from payload
    qa_service = QAService(
        app_settings,
        qa_instance=qa_instance,
        retriever_instance=retriever_instance,
        retriever_settings=retriever_settings,
    )
    

    try:
        # Use the correct method name 'qa' from core QAService
        qa_result = await qa_service.qa(cctree, request.query, source_arg)

        # Save updated impact values to each document's tree.json
        for fn, tree in trees.items():
            t_path = paths.doc_cache_dir(fn) / "tree.json"
            try:
                tree.save_json(str(t_path))
            except Exception as e:
                logger.warning(f"Failed to save updated tree for {fn}: {e}")

    except Exception as e:
        logger.error(f"QA process failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"QA process failed: {e}")

    documents = []
    for doc in qa_result.get("retrieved_documents", []):
        doc_file_name = doc.get("file_name") or primary
        documents.append(
            RetrievalItem(
                page=doc.get("page", 0),
                content=doc.get("content", ""),
                bboxes=doc.get("bboxes", []),
                file_name=doc_file_name,
                score=doc.get("score", 0.0),
            )
        )

    return ChatResponse(
        answer=qa_result.get("answer", "No answer"),
        reasoning_log="",
        retrieved_documents=documents,
        node_impacts=qa_result.get("node_impacts", {}),
    )
