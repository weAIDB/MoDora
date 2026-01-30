from __future__ import annotations

import asyncio
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


async def get_components_async(
    extracted_data: OcrExtractResponse, logger: logging.Logger
) -> ComponentPack:
    """
    异步将 OCR 提取的扁平 Block 列表重组为结构化的 ComponentPack。
    """
    # 1. Structure Analysis
    # 为了避免阻塞主事件循环，放到 executor 中运行
    loop = asyncio.get_running_loop()
    analyzer = StructureAnalyzer()
    co_pack = await loop.run_in_executor(None, analyzer.analyze, extracted_data, logger)

    # 2. Enrichment
    # 使用异步 LLM 客户端
    llm = AsyncQwenLLMClient()
    cropper = PDFCropper()
    enricher = EnrichmentService(llm, cropper)

    # 执行增强
    co_pack = await enricher.enrich_async(co_pack, extracted_data.source)

    return co_pack


def get_components(
    extracted_data: OcrExtractResponse, logger: logging.Logger
) -> ComponentPack:
    """
    (Deprecated) 同步版本，为了兼容旧代码保留，建议迁移到 get_components_async。
    """
    import asyncio
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(get_components_async(extracted_data, logger))


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
