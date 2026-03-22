from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from modora.api.auth import get_optional_current_user
from modora.api.v1.document_access import resolve_document_paths
from modora.core.domain.cctree import CCTree
from modora.core.auth.service import AuthUser
from modora.core.persistence.user_preferences import effective_settings_for_user
from modora.core.settings import Settings
from modora.core.utils.config import settings_from_ui_payload
from modora.core.services.qa_service import QAService
from modora.api.v1.models import ChatRequest, ChatResponse, RetrievalItem

router = APIRouter(tags=["chat"])
logger = logging.getLogger("modora.api")


def _settings_from_payload(
    payload: dict[str, Any] | None,
    *,
    user: AuthUser | None,
) -> tuple[Settings, str | None, Settings, str | None]:
    settings = effective_settings_for_user(Settings.load(), user_id=user.id if user else None)
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
async def chat_endpoint(
    request: ChatRequest,
    user: AuthUser | None = Depends(get_optional_current_user),
):
    settings_payload = request.settings or {}
    identifiers: list[tuple[str, str]] = []
    if request.document_ids:
        identifiers.extend(("document_id", item) for item in request.document_ids)
    elif request.document_id:
        identifiers.append(("document_id", request.document_id))
    elif request.file_names:
        identifiers.extend(("file_name", item) for item in request.file_names)
    elif request.file_name:
        identifiers.append(("file_name", request.file_name))

    if not identifiers:
        raise HTTPException(status_code=400, detail="File name(s) or document id(s) required")

    (
        app_settings,
        qa_instance,
        retriever_settings,
        retriever_instance,
    ) = _settings_from_payload(settings_payload, user=user)

    # Load tree structures for all documents
    trees: dict[str, CCTree] = {}
    source_paths: dict[str, str] = {}
    display_names: dict[str, str] = {}
    document_ids_by_storage_name: dict[str, str] = {}

    for identifier_type, value in identifiers:
        resolved = resolve_document_paths(
            app_settings,
            user=user,
            document_id=value if identifier_type == "document_id" else None,
            file_name=value if identifier_type == "file_name" else None,
        )
        s_path = resolved.source_path
        if not s_path.exists():
            continue

        t_path = resolved.cache_dir / "tree.json"
        if not t_path.exists():
            continue

        try:
            t_dict = json.loads(t_path.read_text(encoding="utf-8"))
            trees[resolved.storage_name] = CCTree.from_dict(t_dict)
            source_paths[resolved.storage_name] = str(s_path)
            display_names[resolved.storage_name] = resolved.display_name
            if resolved.document_id:
                document_ids_by_storage_name[resolved.storage_name] = resolved.document_id
        except Exception as e:
            logger.warning(f"Failed to load tree for {resolved.storage_name}: {e}")

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
            resolved = resolve_document_paths(
                app_settings,
                user=user,
                document_id=document_ids_by_storage_name.get(fn),
                file_name=fn,
            )
            t_path = resolved.cache_dir / "tree.json"
            try:
                tree.save_json(str(t_path))
            except Exception as e:
                logger.warning(f"Failed to save updated tree for {fn}: {e}")

    except Exception as e:
        logger.error(f"QA process failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"QA process failed: {e}")

    documents = []
    for doc in qa_result.get("retrieved_documents", []):
        doc_storage_name = doc.get("file_name") or primary
        documents.append(
            RetrievalItem(
                page=doc.get("page", 0),
                content=doc.get("content", ""),
                bboxes=doc.get("bboxes", []),
                file_name=display_names.get(doc_storage_name, doc_storage_name),
                document_id=document_ids_by_storage_name.get(doc_storage_name),
                score=doc.get("score", 0.0),
            )
        )

    return ChatResponse(
        answer=qa_result.get("answer", "No answer"),
        reasoning_log="",
        retrieved_documents=documents,
        node_impacts=qa_result.get("node_impacts", {}),
    )
