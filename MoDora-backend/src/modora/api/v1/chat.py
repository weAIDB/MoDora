from __future__ import annotations

import json
import logging
from typing import Any
from dataclasses import replace

from fastapi import APIRouter, HTTPException

from modora.core.domain.cctree import CCTree
from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths
from modora.core.services.qa_service import QAService
from modora.api.v1.models import ChatRequest, ChatResponse, RetrievalItem

router = APIRouter(tags=["chat"])
logger = logging.getLogger("modora.api")

def _settings_from_payload(payload: dict[str, Any] | None, *, api_model: str | None = None) -> Settings:
    settings = Settings.load()
    overrides: dict[str, Any] = {}
    if payload:
        if payload.get("apiKey"):
            overrides["api_key"] = payload.get("apiKey")
        if payload.get("baseUrl"):
            overrides["api_base"] = payload.get("baseUrl")
        if payload.get("qaModel") and not api_model:
            api_model = payload.get("qaModel")
    if api_model:
        overrides["api_model"] = api_model
    return replace(settings, **overrides) if overrides else settings

def _llm_mode_from_payload(payload: dict[str, Any] | None, key: str) -> str | None:
    if not payload:
        return None
    val = str(payload.get(key) or "").lower()
    if "local" in val:
        return "local"
    if val:
        return "remote"
    return None

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    settings_payload = request.settings or {}
    file_names = request.file_names or ([] if not request.file_name else [request.file_name])
    if not file_names:
        raise HTTPException(status_code=400, detail="File name(s) required")

    app_settings = _settings_from_payload(settings_payload, api_model=settings_payload.get("qaModel"))
    paths = resolve_paths(app_settings)

    # Use first file for now; multi-file support can be expanded later.
    primary = file_names[0]
    source_path = paths.docs_dir / primary
    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {primary}")

    tree_path = paths.doc_cache_dir(primary) / "tree.json"
    if not tree_path.exists():
        raise HTTPException(status_code=404, detail=f"Tree cache not found for {primary}. Please wait for processing.")

    tree_dict = json.loads(tree_path.read_text(encoding="utf-8"))
    cctree = CCTree.from_dict(tree_dict)

    llm_mode = _llm_mode_from_payload(settings_payload, "qaModel")
    
    # Use the core QAService
    qa_service = QAService(app_settings)

    try:
        # Use the correct method name 'qa' from core QAService
        qa_result = await qa_service.qa(cctree, request.query, str(source_path))
    except Exception as e:
        logger.error(f"QA process failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"QA process failed: {e}")

    documents = []
    for doc in qa_result.get("retrieved_documents", []):
        documents.append(
            RetrievalItem(
                page=doc.get("page", 0),
                content=doc.get("content", ""),
                bboxes=doc.get("bboxes", []),
                file_name=primary,
            )
        )

    return ChatResponse(
        answer=qa_result.get("answer", "No answer"),
        reasoning_log="",
        retrieved_documents=documents,
        node_impacts=qa_result.get("node_impacts", {}),
    )
