from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from dataclasses import replace

from modora.core.infra.llm.factory import AsyncLLMFactory
from modora.core.infra.llm.base import BaseAsyncLLMClient
from modora.core.infra.pdf.cropper import PDFCropper
from modora.core.preprocess import get_components_async
from modora.core.services.constructor import TreeConstructor
from modora.core.services.generator import AsyncMetadataGenerator
from modora.core.services.hierarchy import AsyncLevelGenerator
from modora.core.settings import Settings
from modora.core.services.kb import KnowledgeBaseManager
from modora.core.utils.paths import AppPaths
from modora.core.services.stats import get_component_stats, get_tree_stats
from modora.core.services.task_store import TASK_STATUS
from modora.core.infra.ocr.manager import get_ocr_model
from modora.core.domain.ocr import OcrExtractResponse, OCRBlock
from modora.core.infra.pdf.fallback import extract_pdf_blocks


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
    logger: logging.Logger,
    ocr_res: OcrExtractResponse | None = None,
    mode: str | None = None,
) -> None:
    llm_mode = mode or _resolve_llm_mode(config, "selectedMode")
    llm = AsyncLLMFactory.create(settings, mode=llm_mode)

    if ocr_res is None:
        try:
            model = get_ocr_model()
            if model is None:
                raise ValueError("OCR model not loaded")
            
            pdf_blocks: list[OCRBlock] = []
            for page_blocks in model.predict_iter(str(source_path)):
                pdf_blocks.extend(page_blocks)
            ocr_res = OcrExtractResponse(source=f"file:{source_path}", blocks=pdf_blocks)
        except Exception as e:
            logger.warning(f"ocr extract failed, fallback to pdf text blocks: {e}")
            ocr_res = extract_pdf_blocks(str(source_path))

    cache_dir = paths.doc_cache_dir(source_path.name)
    cache_dir.mkdir(parents=True, exist_ok=True)

    (cache_dir / "ocr.json").write_text(
        json.dumps(ocr_res.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    cp = await get_components_async(ocr_res, logger, llm_client=llm)
    cp.save_json(str(cache_dir / "cp.json"))

    # hierarchy + tree
    cropper = PDFCropper()
    try:
        cp = await AsyncLevelGenerator(llm, cropper).generate_level(
            str(source_path), cp, settings, logger
        )
    except Exception as e:
        logger.error(f"level generation failed: {e}")

    # constructor
    constructor = TreeConstructor(settings, logger)
    tree = constructor.construct_tree(cp)

    # metadata enrichment
    generator = AsyncMetadataGenerator(3, 2.0, llm, logger)
    await generator.get_metadata(tree)

    tree_path = cache_dir / "tree.json"
    tree_path.write_text(
        json.dumps(tree.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def process_document_task(
    source_path: str,
    paths: AppPaths,
    settings: Settings,
    config: dict[str, Any] | None,
    logger: logging.Logger,
    mode: str | None = None,
) -> None:
    filename = Path(source_path).name
    TASK_STATUS.set(filename, "processing")
    logger.info(f"Start processing document: {filename}")

    try:
        await _build_tree(Path(source_path), paths, settings, config, logger, mode=mode)

        # Update KB
        kb_path = paths.cache_dir / "knowledge_base.json"
        kb = KnowledgeBaseManager(kb_path)

        cache_dir = paths.doc_cache_dir(filename)
        counts, variance, pages = get_component_stats(cache_dir / "ocr.json")
        node_cnt, leaf_cnt, depth = get_tree_stats(cache_dir / "tree.json")

        # Semantic tags
        llm = AsyncLLMFactory.create(settings, mode=mode)
        tree_dict = json.loads((cache_dir / "tree.json").read_text(encoding="utf-8"))
        
        # Simple text extraction for tagging
        all_text = []
        def _collect(d):
            if d.get("data"): all_text.append(str(d["data"]))
            for c in d.get("children", {}).values(): _collect(c)
        _collect(tree_dict)
        
        semantic_tags = await _generate_semantic_tags(all_text, llm)

        kb.update_doc_info(
            filename,
            {
                "stats": {
                    "pages": pages,
                    "counts": counts,
                    "variance": variance,
                    "nodes": node_cnt,
                    "leaves": leaf_cnt,
                    "depth": depth,
                },
                "semantic_tags": semantic_tags,
                "added_at": datetime.now().isoformat(),
            },
        )

        TASK_STATUS.set(filename, "completed")
        logger.info(f"Finished processing document: {filename}")
    except Exception as e:
        logger.error(f"Failed to process document {filename}: {e}", exc_info=True)
        TASK_STATUS.set(filename, "failed")
