from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException

from modora.api.auth import get_optional_current_user
from modora.api.v1.document_access import resolve_document_paths
from modora.core.auth.service import AuthUser
from modora.core.settings import Settings
from modora.core.services.kb import KnowledgeBaseManager
from modora.core.services.stats import get_component_stats, get_tree_stats
from modora.api.v1.models import (
    DocStatsResponse,
    SessionStatsRequest,
    SessionStatsResponse,
)

router = APIRouter(tags=["stats"])
logger = logging.getLogger("modora.api")


@router.get("/docs/stats/{file_name}", response_model=DocStatsResponse)
async def get_doc_stats(
    file_name: str,
    user: AuthUser | None = Depends(get_optional_current_user),
):
    return await _get_doc_stats(file_name=file_name, document_id=None, user=user)


@router.get("/documents/{document_id}/stats", response_model=DocStatsResponse)
async def get_doc_stats_by_document_id(
    document_id: str,
    user: AuthUser = Depends(get_optional_current_user),
):
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return await _get_doc_stats(file_name=None, document_id=document_id, user=user)


async def _get_doc_stats(
    *,
    file_name: str | None,
    document_id: str | None,
    user: AuthUser | None,
):
    settings = Settings.load()
    resolved = resolve_document_paths(
        settings,
        user=user,
        document_id=document_id,
        file_name=file_name,
    )
    cache_dir = resolved.cache_dir

    ocr_path = cache_dir / "ocr.json"
    tree_path = cache_dir / "tree.json"
    if not ocr_path.exists() or not tree_path.exists():
        raise HTTPException(status_code=404, detail=f"Stats not found for {resolved.display_name}")

    counts, variance, page_count = get_component_stats(ocr_path)
    nodes, leaves, depth = get_tree_stats(tree_path)

    kb = KnowledgeBaseManager(resolved.kb_path)
    doc_info = kb.get_doc_info(resolved.storage_name) or {}
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
async def get_session_stats(
    request: SessionStatsRequest,
    user: AuthUser | None = Depends(get_optional_current_user),
):
    identifiers = []
    if request.document_ids:
        identifiers.extend(("document_id", item) for item in request.document_ids)
    if request.file_names:
        identifiers.extend(("file_name", item) for item in request.file_names)

    if not identifiers:
        return SessionStatsResponse(
            total_files=0,
            avg_pages=0.0,
            avg_nodes=0.0,
            avg_depth=0.0,
            total_counts={
                "chart": 0,
                "image": 0,
                "table": 0,
                "layout_misc": 0,
                "text": 0,
            },
            avg_variance=0.0,
        )

    total_pages = 0
    total_nodes = 0
    total_depth = 0
    total_counts = {"chart": 0, "image": 0, "table": 0, "layout_misc": 0, "text": 0}
    total_variance = 0.0
    valid_count = 0

    settings = Settings.load()

    for identifier_type, value in identifiers:
        resolved = resolve_document_paths(
            settings,
            user=user,
            document_id=value if identifier_type == "document_id" else None,
            file_name=value if identifier_type == "file_name" else None,
        )
        cache_dir = resolved.cache_dir
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
        raise HTTPException(
            status_code=404, detail="No valid stats found for session files"
        )

    return SessionStatsResponse(
        total_files=valid_count,
        avg_pages=total_pages / valid_count,
        avg_nodes=total_nodes / valid_count,
        avg_depth=total_depth / valid_count,
        total_counts=total_counts,
        avg_variance=total_variance / valid_count,
    )
