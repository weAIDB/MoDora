from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException

from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths
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

    settings = Settings.load()
    paths = resolve_paths(settings)

    total_pages = 0
    total_nodes = 0
    total_depth = 0
    total_counts = {"chart": 0, "image": 0, "table": 0, "layout_misc": 0, "text": 0}
    total_variance = 0.0
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
