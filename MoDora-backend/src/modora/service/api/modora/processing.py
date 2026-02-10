from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from modora.core.infra.llm import AsyncLLMFactory, BaseAsyncLLMClient
from modora.core.infra.pdf import PDFCropper
from modora.core.preprocess import get_components_async
from modora.core.services.constructor import TreeConstructor
from modora.core.services.generator import AsyncMetadataGenerator
from modora.core.services.hierarchy import AsyncLevelGenerator
from modora.core.settings import Settings
from modora.service.api.modora.kb import KnowledgeBaseManager
from modora.service.api.modora.paths import AppPaths
from modora.service.api.modora.stats import get_component_stats, get_tree_stats
from modora.service.api.modora.task_store import TASK_STATUS
from modora.service.api.ocr.router import OCRExtractPdfRequest, ocr_extract_pdf
from modora.core.infra.ocr.manager import ensure_ocr_model_loaded, get_ocr_model
from modora.core.domain.ocr import OcrExtractResponse
from modora.service.api.modora.pdf_fallback import extract_pdf_blocks
from dataclasses import replace


def _resolve_llm_mode(config: dict[str, Any] | None, key: str) -> str | None:
    if not config:
        return None
    val = str(config.get(key) or "").lower()
    if "local" in val:
        return "local"
    if val:
        return "remote"
    return None


def _settings_with_overrides(
    base: Settings, overrides: dict[str, Any] | None, *, api_model: str | None = None
) -> Settings:
    payload: dict[str, Any] = {}
    if overrides:
        if overrides.get("apiKey"):
            payload["api_key"] = overrides.get("apiKey")
        if overrides.get("baseUrl"):
            payload["api_base"] = overrides.get("baseUrl")
    if api_model:
        payload["api_model"] = api_model
    return replace(base, **payload) if payload else base


async def _generate_semantic_tags(
    cp_text: list[str],
    llm: BaseAsyncLLMClient,
    max_tags: int = 5,
) -> list[str]:
    if not cp_text:
        return ["No Text Content"]
    full_text = "\n".join(cp_text)[:2000]
    try:
        raw = await llm.generate_metadata(full_text, num=3)
    except Exception:
        return ["Analysis Failed"]
    tags = [t.strip() for t in raw.split(";") if t.strip()]
    return tags[:max_tags] if tags else ["No Text Content"]


async def _build_tree(
    source_path: Path,
    paths: AppPaths,
    settings: Settings,
    config: dict[str, Any] | None,
    logger,
    ocr_res: OcrExtractResponse | None = None,
) -> None:
    llm_mode = _resolve_llm_mode(config, "treeModel")
    llm = AsyncLLMFactory.create(settings, mode=llm_mode)

    if ocr_res is None:
        try:
            ocr_res = ocr_extract_pdf(OCRExtractPdfRequest(file_path=str(source_path)))
        except Exception as e:
            logger.warning(f"ocr extract failed, fallback to pdf text blocks: {e}")
            ocr_res = extract_pdf_blocks(str(source_path))
    cache_dir = paths.doc_cache_dir(source_path.name)
    cache_dir.mkdir(parents=True, exist_ok=True)

    if hasattr(ocr_res, "model_dump"):
        ocr_payload = ocr_res.model_dump()
    else:
        ocr_payload = ocr_res.dict()
    (cache_dir / "ocr.json").write_text(
        json.dumps(ocr_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    cp = await get_components_async(ocr_res, logger)
    cp.save_json(str(cache_dir / "cp.json"))

    # hierarchy + tree
    cropper = PDFCropper()
    try:
        cp = await AsyncLevelGenerator(llm, cropper).generate_level(
            source_path=str(source_path), cp=cp, config=settings, logger=logger
        )
    except Exception as e:
        logger.warning(f"generate_level failed: {e}")

    tree = TreeConstructor(settings, logger).construct_tree(cp)
    try:
        await AsyncMetadataGenerator(2, 2.0, llm, logger).get_metadata(tree)
    except Exception as e:
        logger.warning(f"metadata generation failed: {e}")

    tree.save_json(str(cache_dir / "tree.json"))

    # stats and tags
    counts, variance, pages = get_component_stats(cache_dir / "ocr.json")
    nodes, leaves, depth = get_tree_stats(cache_dir / "tree.json")

    tags: list[str] = []
    if pages > 20:
        tags.append("Long")
    elif pages > 5:
        tags.append("Medium")
    else:
        tags.append("Short")
    if counts.get("table", 0) > 3:
        tags.append("Table-Rich")
    if counts.get("chart", 0) > 3:
        tags.append("Chart-Rich")
    if counts.get("image", 0) > 5:
        tags.append("Image-Rich")
    if variance > 0.5:
        tags.append("Complex Layout")
    if depth > 5:
        tags.append("Deep Hierarchy")

    semantic_tags: list[str]
    cp_text = [co.data for co in cp.body if co.type == "text"][:10]
    semantic_tags = await _generate_semantic_tags(cp_text, llm)

    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    kb.update_doc_info(
        source_path.name,
        {
            "tags": tags,
            "semantic_tags": semantic_tags,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stats": {
                "pages": pages,
                "counts": counts,
                "variance": variance,
                "nodes": nodes,
                "leaves": leaves,
                "depth": depth,
            },
        },
    )


def process_document_task(
    file_path: str,
    paths: AppPaths,
    settings: Settings,
    config: dict[str, Any] | None,
    logger,
) -> None:
    filename = Path(file_path).name
    TASK_STATUS.set(filename, "processing")
    try:
        try:
            ensure_ocr_model_loaded(settings, logger)
        except Exception as e:
            logger.warning(f"ocr init failed: {e}")
        ocr_res: OcrExtractResponse | None = None
        if get_ocr_model() is None:
            logger.warning("ocr model not available, using pdf text fallback")
            ocr_res = extract_pdf_blocks(file_path)
        settings = _settings_with_overrides(settings, config, api_model=(config or {}).get("treeModel"))
        asyncio.run(_build_tree(Path(file_path), paths, settings, config, logger, ocr_res))
        TASK_STATUS.set(filename, "completed")
    except Exception as e:
        logger.error(f"processing failed for {filename}: {e}")
        TASK_STATUS.set(filename, "failed")
