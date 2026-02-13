from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from modora.core.preprocess import get_components_async, build_tree_async
from modora.core.services.kb import KnowledgeBaseManager
from modora.core.utils.paths import AppPaths
from modora.core.services.stats import get_component_stats, get_tree_stats
from modora.core.services.task_store import TASK_STATUS
from modora.core.infra.ocr.manager import get_ocr_model
from modora.core.infra.pdf.fallback import extract_pdf_blocks
from modora.core.domain.ocr import OcrExtractResponse, OCRBlock
from modora.core.settings import Settings


def _generate_auto_tags(
    counts: dict[str, int],
    variance: float,
    pages: int,
    depth: int,
) -> list[str]:
    """Generates automatic tags based on statistical features (consistent with legacy rules)."""
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

    return tags


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
        source_p = Path(source_path)
        # 1. Prioritize using the OCR model; fallback to PDF text extraction when unavailable to ensure the process continues.
        model = None
        try:
            model = get_ocr_model(
                settings=settings, logger=logger, create_if_missing=True
            )
        except Exception as e:
            logger.warning(f"OCR model load failed, using PDF text fallback: {e}")
        if model is None:
            logger.warning("OCR model not available, using PDF text fallback")
            ocr_res = extract_pdf_blocks(str(source_p))
        else:
            try:
                pdf_blocks: list[OCRBlock] = []
                for page_blocks in model.predict_iter(str(source_p)):
                    pdf_blocks.extend(page_blocks)
                ocr_res = OcrExtractResponse(
                    source=f"file:{source_p}", blocks=pdf_blocks
                )
            except Exception as e:
                logger.warning(f"OCR predict failed, using PDF text fallback: {e}")
                ocr_res = extract_pdf_blocks(str(source_p))

        # 2. Cache OCR results
        cache_dir = paths.doc_cache_dir(filename)
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "ocr.json").write_text(
            json.dumps(ocr_res.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 3. Call the two core orchestration functions in preprocess.py
        # Get ComponentPack
        cp = await get_components_async(
            ocr_res, logger, settings=settings, config=config
        )
        cp.save_json(str(cache_dir / "cp.json"))

        # Get the final CCTree
        tree = await build_tree_async(
            cp,
            logger,
            source_path=str(source_p),
            settings=settings,
            config=config,
        )

        # 4. Semantic tags (extracted directly from root node metadata)
        raw_metadata = tree.root.metadata or ""
        semantic_tags = [t.strip() for t in raw_metadata.split(";") if t.strip()][:5]
        if not semantic_tags:
            semantic_tags = ["Document"]

        # 5. Persist Tree
        tree_path = cache_dir / "tree.json"
        tree_path.write_text(
            json.dumps(tree.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 6. Update KB and statistical information
        kb_path = paths.cache_dir / "knowledge_base.json"
        kb = KnowledgeBaseManager(kb_path)

        counts, variance, pages = get_component_stats(cache_dir / "ocr.json")
        node_cnt, leaf_cnt, depth = get_tree_stats(cache_dir / "tree.json")
        auto_tags = _generate_auto_tags(counts, variance, pages, depth)

        kb.update_doc_info(
            filename,
            {
                "tags": auto_tags,
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
