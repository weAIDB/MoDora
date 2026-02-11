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
    """
    异步将 OCR 提取的扁平 Block 列表重组并增强为结构化的 ComponentPack。

    该函数编排了以下工作流：
    1. 利用 StructureAnalyzer 对元素合并得到 Correlated-Component
    2. 利用 EnrichmentService 对非文本组件（如图片、表格）进行 LLM 语义增强。

    参数:
        extracted_data: 包含 OCR 原始结果的数据对象。
        logger: 日志实例。

    返回:
        ComponentPack: 经过结构化重组和语义增强的组件包。
    """
    # 1. 结构分析 (Structure Analysis)
    # 为了避免阻塞主事件循环，放到 executor 中运行（处理 OCR 列表可能涉及大量循环计算）
    loop = asyncio.get_running_loop()
    analyzer = StructureAnalyzer()
    co_pack = await loop.run_in_executor(None, analyzer.analyze, extracted_data, logger)

    # 2. 信息增强 (Enrichment)
    base_settings = settings or Settings.load()
    enrich_settings, enrich_mode, _ = settings_from_ui_payload(
        base_settings, config, module_key="enrichment"
    )
    llm = AsyncLLMFactory.create(enrich_settings, mode=enrich_mode or "local")
    cropper = PDFCropper()
    enricher = EnrichmentService(llm, cropper)

    # 执行增强
    co_pack = await enricher.enrich_async(co_pack, extracted_data.source)

    return co_pack


async def build_tree_async(
    cp: ComponentPack,
    logger: logging.Logger,
    source_path: str = "",
    settings: Settings | None = None,
    config: dict | None = None,
):
    """
    异步构建 CCTree 文档树。

    该函数编排了以下工作流：
    1. 利用 AsyncLevelGenerator 生成或修正标题层级。
    2. 利用 TreeConstructor 根据层级结构构造树。
    3. 利用 AsyncMetadataGenerator 为树节点生成元数据摘要。

    参数:
        cp: 初始组件包。
        logger: 日志实例。
        source_path: PDF 源文件路径，用于层级生成时的视觉参考。

    返回:
        CCTree: 构建完成并包含元数据的文档树。
    """
    base_settings = settings or Settings.load()
    level_settings, level_mode, _ = settings_from_ui_payload(
        base_settings, config, module_key="levelGenerator"
    )
    metadata_settings, metadata_mode, _ = settings_from_ui_payload(
        base_settings, config, module_key="metadataGenerator"
    )

    llm_level = AsyncLLMFactory.create(level_settings, mode=level_mode or "remote")
    llm_metadata = AsyncLLMFactory.create(
        metadata_settings, mode=metadata_mode or "local"
    )

    cropper = PDFCropper()
    generator = AsyncMetadataGenerator(
        n0=2, growth_rate=2.0, logger=logger, llm_client=llm_metadata
    )
    constructor = TreeConstructor(base_settings, logger)

    # 1. 标题层级增强
    cp = await AsyncLevelGenerator(llm_level, cropper).generate_level(
        source_path=source_path, cp=cp, config=level_settings, logger=logger
    )

    # 2. 构造树结构
    cctree = constructor.construct_tree(cp)

    # 3. 语义元数据生成
    await generator.get_metadata(cctree)

    return cctree
