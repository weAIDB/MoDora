from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from modora.core.domain import ComponentPack, OcrExtractResponse
from modora.core.infra.llm import AsyncLLMFactory
from modora.core.infra.pdf import PDFCropper
from modora.core.services import (
    StructureAnalyzer,
    EnrichmentService,
    TreeConstructor,
    AsyncLevelGenerator,
    AsyncMetadataGenerator,
)
from modora.core.settings import Settings
from modora.core.utils.config import settings_from_ui_payload


async def get_components_async(
    extracted_data: OcrExtractResponse,
    logger: logging.Logger,
    settings: Settings | None = None,
    config: dict | None = None,
) -> ComponentPack:
    """Asynchronously reassembles and enhances flat OCR-extracted Block lists into a structured ComponentPack.

    This function orchestrates the following workflow:
    1. Uses StructureAnalyzer to merge elements into Correlated-Components.
    2. Uses EnrichmentService to perform LLM semantic enhancement on non-text components (e.g., images, tables).

    Args:
        extracted_data: Data object containing raw OCR results.
        logger: Logging instance.
        settings: Optional Settings object.
        config: Optional configuration dictionary.

    Returns:
        ComponentPack: A component pack that has been structurally reassembled and semantically enhanced.
    """
    # 1. Structure Analysis
    # To avoid blocking the main event loop, run in an executor (OCR list processing may involve heavy computation)
    loop = asyncio.get_running_loop()
    analyzer = StructureAnalyzer()
    co_pack = await loop.run_in_executor(None, analyzer.analyze, extracted_data, logger)

    # 2. Enrichment
    base_settings = settings or Settings.load()
    enrich_settings, _, enrich_instance_id, _ = settings_from_ui_payload(
        base_settings, config, module_key="enrichment"
    )
    llm = AsyncLLMFactory.create(enrich_settings, instance_id=enrich_instance_id)
    cropper = PDFCropper()
    enricher = EnrichmentService(llm, cropper)

    # Execute enhancement
    co_pack = await enricher.enrich_async(co_pack, extracted_data.source)

    return co_pack


async def build_tree_async(
    cp: ComponentPack,
    logger: logging.Logger,
    source_path: str = "",
    interim_tree_path: str | None = None,
    settings: Settings | None = None,
    config: dict | None = None,
):
    """Asynchronously builds the CCTree document tree.

    This function orchestrates the following workflow:
    1. Uses AsyncLevelGenerator to generate or correct heading levels.
    2. Uses TreeConstructor to construct the tree based on the level structure.
    3. Uses AsyncMetadataGenerator to generate metadata summaries for tree nodes.

    Args:
        cp: Initial component pack.
        logger: Logging instance.
        source_path: Path to the PDF source file for visual reference during level generation.
        settings: Optional Settings object.
        config: Optional configuration dictionary.

    Returns:
        CCTree: The completed document tree containing metadata.
    """
    base_settings = settings or Settings.load()
    level_settings, _, level_instance_id, _ = settings_from_ui_payload(
        base_settings, config, module_key="levelGenerator"
    )
    metadata_settings, _, metadata_instance_id, _ = settings_from_ui_payload(
        base_settings, config, module_key="metadataGenerator"
    )

    llm_level = AsyncLLMFactory.create(level_settings, instance_id=level_instance_id)
    llm_metadata = AsyncLLMFactory.create(
        metadata_settings, instance_id=metadata_instance_id
    )

    cropper = PDFCropper()
    generator = AsyncMetadataGenerator(
        n0=2, growth_rate=2.0, logger=logger, llm_client=llm_metadata
    )
    constructor = TreeConstructor(base_settings, logger)

    # 1. Heading level enhancement
    logger.info("build_tree: starting level generation", extra={"source_path": source_path})
    cp = await AsyncLevelGenerator(llm_level, cropper).generate_level(
        source_path=source_path, cp=cp, config=level_settings, logger=logger
    )
    logger.info("build_tree: level generation finished", extra={"source_path": source_path})

    # 2. Construct tree structure
    logger.info("build_tree: constructing tree", extra={"source_path": source_path})
    cctree = constructor.construct_tree(cp)
    logger.info(
        "build_tree: tree construction finished",
        extra={"source_path": source_path, "root_children": len(cctree.root.children)},
    )

    if interim_tree_path:
        tree_path = Path(interim_tree_path)
        await asyncio.to_thread(
            tree_path.write_text,
            json.dumps(cctree.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "build_tree: wrote interim tree",
            extra={"source_path": source_path, "tree_path": str(tree_path)},
        )

    # 3. Semantic metadata generation
    logger.info("build_tree: starting metadata generation", extra={"source_path": source_path})
    await generator.get_metadata(cctree)
    logger.info("build_tree: metadata generation finished", extra={"source_path": source_path})

    return cctree
