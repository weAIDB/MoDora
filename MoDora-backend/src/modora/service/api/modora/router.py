from __future__ import annotations

import json
import logging
from dataclasses import replace
import os
from pathlib import Path
from typing import Any

import fitz
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from modora.core.domain.cctree import CCTree, CCTreeNode
from modora.core.settings import Settings
from modora.service.api.modora.kb import KnowledgeBaseManager
from modora.service.api.modora.models import (
    ChatRequest,
    ChatResponse,
    DocStatsResponse,
    NodeUpdateRequest,
    RetrievalItem,
    SessionStatsRequest,
    SessionStatsResponse,
    TreeRequest,
    TreeResponse,
    TreeUpdateRequest,
    UpdateTagsRequest,
)
from modora.service.api.modora.paths import resolve_paths
from modora.service.api.modora.processing import process_document_task
from modora.service.api.modora.qa_service import QAService
from modora.service.api.modora.stats import get_component_stats, get_tree_stats
from modora.service.api.modora.task_store import TASK_STATUS
from modora.service.api.modora.tree_utils import (
    convert_tree_to_vueflow,
    dict_to_tree,
    reconstruct_tree_from_elements,
    validate_tree_structure,
    TreeNode,
)

router = APIRouter(prefix="/api", tags=["modora"])
logger = logging.getLogger("modora.service")


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


@router.get("/pdf/{file_name}/{page_index}/image")
def get_pdf_image(file_name: str, page_index: int):
    settings = Settings.load()
    paths = resolve_paths(settings)
    source_path = paths.docs_dir / file_name
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        doc = fitz.open(str(source_path))
        if page_index < 1 or page_index > len(doc):
            doc.close()
            raise HTTPException(status_code=400, detail="Invalid page index")

        page = doc[page_index - 1]
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        doc.close()
        return StreamingResponse(iter([img_data]), media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/status/{filename}")
def get_task_status(filename: str):
    settings = Settings.load()
    paths = resolve_paths(settings)
    status = TASK_STATUS.get(filename)
    if status == "unknown":
        doc_cache = paths.doc_cache_dir(filename)
        if (doc_cache / "tree.json").exists():
            return {"status": "completed"}
    return {"status": status}


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: str | None = Form(None),
):
    cfg: dict[str, Any] | None = None
    if settings:
        try:
            cfg = json.loads(settings)
        except json.JSONDecodeError:
            cfg = {}

    app_settings = _settings_from_payload(cfg)
    paths = resolve_paths(app_settings)

    file_location = paths.docs_dir / file.filename
    try:
        with file_location.open("wb") as buffer:
            buffer.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {e}")

    TASK_STATUS.set(file.filename, "pending")
    background_tasks.add_task(
        process_document_task,
        str(file_location),
        paths,
        app_settings,
        cfg,
        logger,
    )
    return {
        "filename": file.filename,
        "status": "uploaded",
        "message": "File uploaded. Processing in background.",
    }


@router.get("/kb/docs")
def get_kb_docs():
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    return kb.get_all_docs()


@router.get("/kb/tags")
def get_kb_tags():
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    return kb.get_tag_library()


@router.post("/kb/doc/tags")
def update_kb_doc_tags(request: UpdateTagsRequest):
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    kb.update_doc_tags(request.file_name, request.tags)
    return {"status": "success"}


@router.delete("/kb/tag/{tag}")
def delete_kb_tag(tag: str):
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    kb.delete_tag_from_library(tag)
    return {"status": "success"}


@router.delete("/kb/delete/{file_name}")
def delete_kb_doc(file_name: str):
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")

    source_path = paths.docs_dir / file_name
    if source_path.exists():
        source_path.unlink()

    cache_path = paths.doc_cache_dir(file_name)
    if cache_path.exists():
        for p in cache_path.rglob("*"):
            if p.is_file():
                p.unlink()
        for p in sorted(cache_path.rglob("*"), reverse=True):
            if p.is_dir():
                p.rmdir()
        cache_path.rmdir()

    kb.delete_doc(file_name)
    return {"status": "success", "message": f"File {file_name} deleted successfully"}


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
    qa = QAService(app_settings, logger, llm_mode=llm_mode)

    try:
        qa_result = await qa.answer_question(request.query, cctree, str(source_path))
    except Exception as e:
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


@router.post("/tree", response_model=TreeResponse)
async def get_document_tree(request: TreeRequest):
    settings = Settings.load()
    paths = resolve_paths(settings)
    tree_path = paths.doc_cache_dir(request.file_name) / "tree.json"
    if not tree_path.exists():
        raise HTTPException(status_code=404, detail="Tree cache not found.")

    tree_dict = json.loads(tree_path.read_text(encoding="utf-8"))
    elements = convert_tree_to_vueflow(tree_dict, root_label=request.file_name)
    return TreeResponse(elements=elements)


@router.post("/tree/update")
def update_tree_endpoint(request: TreeUpdateRequest):
    settings = Settings.load()
    paths = resolve_paths(settings)

    tree_path = paths.doc_cache_dir(request.file_name) / "tree.json"
    if not tree_path.exists():
        raise HTTPException(status_code=404, detail=f"Tree cache not found: {tree_path}")

    original_tree_dict = json.loads(tree_path.read_text(encoding="utf-8"))
    try:
        new_tree_dict = reconstruct_tree_from_elements(
            request.elements, original_tree_dict, request.file_name
        )
        validate_tree_structure(new_tree_dict)
        tree_path.write_text(
            json.dumps(new_tree_dict, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"status": "success", "message": "Tree structure updated."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid tree structure: {ve}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tree/node/update")
def update_node_endpoint(request: NodeUpdateRequest):
    settings = Settings.load()
    paths = resolve_paths(settings)
    tree_path = paths.doc_cache_dir(request.file_name) / "tree.json"
    if not tree_path.exists():
        raise HTTPException(status_code=404, detail="Tree not found")

    try:
        tree_dict = json.loads(tree_path.read_text(encoding="utf-8"))
        root = dict_to_tree(tree_dict, root_title=request.file_name)

        current_node = root
        parent_node = None
        path = list(request.target_path)
        if path:
            first_segment = path[0]
            if first_segment == root.title or first_segment == "Document Root":
                path = path[1:]

        for title in path:
            parent_node = current_node
            found = current_node.find_child(title)
            if not found:
                raise HTTPException(status_code=404, detail=f"Node not found: {title}")
            current_node = found

        if request.action == "update":
            if request.new_data:
                current_node.title = request.new_data.get("title", current_node.title)
                current_node.type = request.new_data.get("type", current_node.type)
                current_node.data = request.new_data.get("data", current_node.data)
                current_node.metadata = request.new_data.get("metadata", current_node.metadata)
        elif request.action == "delete":
            if parent_node:
                parent_node.delete_child(current_node)
            else:
                raise HTTPException(status_code=400, detail="Cannot delete root node")
        elif request.action == "add":
            if request.new_data:
                new_child = TreeNode(
                    title=request.new_data.get("title", "New Node"),
                    typ=request.new_data.get("type", "text"),
                    data=request.new_data.get("data", ""),
                )
                current_node.insert_child(new_child)
        else:
            raise HTTPException(status_code=400, detail="Unknown action")

        new_tree_dict = root.to_dict()
        tree_path.write_text(
            json.dumps(new_tree_dict, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"status": "success", "message": f"Node {request.action}d successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docs/stats/{file_name}", response_model=DocStatsResponse)
async def get_doc_stats(file_name: str):
    settings = Settings.load()
    paths = resolve_paths(settings)
    cache_dir = paths.doc_cache_dir(file_name)

    ocr_path = cache_dir / "ocr.json"
    tree_path = cache_dir / "tree.json"
    if not ocr_path.exists() or not tree_path.exists():
        raise HTTPException(status_code=404, detail=f"Stats not found for {file_name}")

    counts, variance, page_count = get_component_stats(ocr_path)
    nodes, leaves, depth = get_tree_stats(tree_path)

    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    doc_info = kb.get_doc_info(file_name) or {}
    tags = doc_info.get("tags", [])
    semantic_tags = doc_info.get("semantic_tags", [])

    return DocStatsResponse(
        pages=page_count,
        counts=counts,
        variance=variance,
        nodes=nodes,
        leaves=leaves,
        depth=depth,
        tags=tags,
        semantic_tags=semantic_tags,
    )


@router.post("/session/stats", response_model=SessionStatsResponse)
async def get_session_stats(request: SessionStatsRequest):
    file_names = request.file_names
    if not file_names:
        return SessionStatsResponse(
            total_files=0,
            avg_pages=0,
            avg_nodes=0,
            avg_depth=0,
            total_counts={
                "chart": 0,
                "image": 0,
                "table": 0,
                "layout_misc": 0,
                "text": 0,
            },
            avg_variance=0,
        )

    settings = Settings.load()
    paths = resolve_paths(settings)

    total_pages = 0
    total_nodes = 0
    total_depth = 0
    total_counts = {"chart": 0, "image": 0, "table": 0, "layout_misc": 0, "text": 0}
    total_variance = 0
    valid_count = 0

    for file_name in file_names:
        cache_dir = paths.doc_cache_dir(file_name)
        ocr_path = cache_dir / "ocr.json"
        tree_path = cache_dir / "tree.json"
        if not ocr_path.exists() or not tree_path.exists():
            continue
        counts, variance, pages = get_component_stats(ocr_path)
        nodes, leaves, depth = get_tree_stats(tree_path)

        total_pages += pages
        total_nodes += nodes
        total_depth += depth
        total_variance += variance
        for k, v in counts.items():
            total_counts[k] = total_counts.get(k, 0) + v
        valid_count += 1

    if valid_count == 0:
        raise HTTPException(status_code=404, detail="No valid stats found for session files")

    return SessionStatsResponse(
        total_files=valid_count,
        avg_pages=total_pages / valid_count,
        avg_nodes=total_nodes / valid_count,
        avg_depth=total_depth / valid_count,
        total_counts=total_counts,
        avg_variance=total_variance / valid_count,
    )
