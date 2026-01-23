from __future__ import annotations

import logging

from modora.core.domain.component import ComponentPack
from modora.core.domain.ocr import OcrExtractResponse
from modora.core.services.structure import StructureAnalyzer
from modora.core.services.enrichment import EnrichmentService
from modora.core.infra.llm.qwen import AsyncQwenLLMClient, QwenLLMClient
from modora.core.infra.pdf.cropper import PDFCropper
from modora.core.services.constructor import TreeConstructor
from modora.core.services.hierarchy import AsyncLevelGenerator, LevelGenerator
from modora.core.services.generator import AsyncMetadataGenerator
from modora.core.settings import Settings


def get_components(
    extracted_data: OcrExtractResponse, logger: logging.Logger
) -> ComponentPack:
    """
    将 OCR 提取的扁平 Block 列表重组为结构化的 ComponentPack。

    此函数现在充当应用服务编排器 (Orchestrator)：
    1. 调用 StructureAnalyzer 进行结构分析。
    2. 调用 EnrichmentService 进行信息增强。
    """
    # 1. Structure Analysis
    analyzer = StructureAnalyzer()
    co_pack = analyzer.analyze(extracted_data, logger)

    # 2. Enrichment
    # 使用默认的适配器实现
    llm = QwenLLMClient()
    cropper = PDFCropper()
    enricher = EnrichmentService(llm, cropper)

    # 执行增强
    co_pack = enricher.enrich(co_pack, extracted_data.source)

    return co_pack


def build_tree(cp: ComponentPack, logger: logging.Logger, source_path: str = ""):
    settings = Settings.load()
    llm = QwenLLMClient()
    cropper = PDFCropper()
    if source_path:
        cp = LevelGenerator(llm, cropper).generate_level(
            source_path=source_path, cp=cp, config=settings, logger=logger
        )
    constructor = TreeConstructor(settings, logger)
    return constructor.construct_tree(cp)


async def build_tree_async(
    cp: ComponentPack, logger: logging.Logger, source_path: str = ""
):
    settings = Settings.load()
    llm = AsyncQwenLLMClient()
    cropper = PDFCropper()
    generator = AsyncMetadataGenerator(
        n0=2, growth_rate=2.0, logger=logger, llm_client=llm
    )
    constructor = TreeConstructor(settings, logger)

    if source_path:
        cp = await AsyncLevelGenerator(llm, cropper).generate_level(
            source_path=source_path, cp=cp, config=settings, logger=logger
        )
    cctree = constructor.construct_tree(cp)
    await generator.get_metadata(cctree)
    return cctree
