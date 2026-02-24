from __future__ import annotations

import asyncio
import logging

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
    cp = await AsyncLevelGenerator(llm_level, cropper).generate_level(
        source_path=source_path, cp=cp, config=level_settings, logger=logger
    )

    # 2. Construct tree structure
    cctree = constructor.construct_tree(cp)

    # 3. Semantic metadata generation
    await generator.get_metadata(cctree)

    return cctree
