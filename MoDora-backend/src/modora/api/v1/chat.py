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

def _settings_from_payload(payload: dict[str, Any] | None) -> tuple[Settings, str | None]:
    settings = Settings.load()
    mode = None
    if payload:
        mode = payload.get("selectedMode")
        
        # 即使只传 mode，我们也允许覆盖 apiKey 和 baseUrl，以便用户在前端临时修改
        overrides: dict[str, Any] = {}
        if payload.get("apiKey"):
            overrides["api_key"] = payload.get("apiKey")
        if payload.get("baseUrl"):
            overrides["api_base"] = payload.get("baseUrl")
        
        if overrides:
            settings = replace(settings, **overrides)
            
    return settings, mode

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    settings_payload = request.settings or {}
    file_names = request.file_names or ([] if not request.file_name else [request.file_name])
    if not file_names:
        raise HTTPException(status_code=400, detail="File name(s) required")

    app_settings, mode = _settings_from_payload(settings_payload)
    paths = resolve_paths(app_settings)

    # 加载所有文档的树结构
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

    # 根据文档数量决定是单文档还是多文档
    if len(trees) > 1:
        # 多文档：合并树
        cctree = CCTree.merge_multi_trees(trees)
        source_arg = source_paths
        primary = "multi_doc_session" # 仅作为标识
    else:
        # 单文档：保持原样
        primary = list(trees.keys())[0]
        cctree = trees[primary]
        source_arg = source_paths[primary]

    # Use the core QAService with the overrides from payload
    qa_service = QAService(app_settings, mode=mode)

    try:
        # Use the correct method name 'qa' from core QAService
        qa_result = await qa_service.qa(cctree, request.query, source_arg)
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
