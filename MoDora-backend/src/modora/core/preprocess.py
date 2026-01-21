from __future__ import annotations

import logging

from typing import Any

from modora.core.domain.component import TITLE, Component, Location, ComponentPack
from modora.core.infra.llm.qwen import qwen_annotation
from modora.core.infra.pdf.cropper import co_to_base64
from modora.service.api.ocr.router import OcrExtractResponse


def information_enrichment(source: str, component: Component) -> tuple[str, Any, str]:
    base64 = co_to_base64(source, component)
    return qwen_annotation(base64, component.type)


def get_components(
    extracted_data: OcrExtractResponse, logger: logging.Logger
) -> ComponentPack:
    """
    将 OCR 提取的扁平 Block 列表重组为结构化的 ComponentPack。

    主要逻辑：
    1. 遍历 OCR blocks，按顺序归类为 Text, Figure, Header, Footer 等。
    2. 使用启发式规则（位置、前后文）将 Figure Title 关联到对应的 Figure。
    3. 聚合同一页的 Header/Footer/Number/Aside。
    4. 对 Image/Chart/Table 组件调用 LLM 进行信息增强（生成 title/metadata/content）。

    Args:
        extracted_data: OCR 原始结果
        logger: 日志记录器

    Returns:
        结构化的组件包
    """
    # Initial sequence
    co_pack = ComponentPack()
    header = co_pack.supplement.header
    footer = co_pack.supplement.footer
    number = co_pack.supplement.number
    aside = co_pack.supplement.aside

    ocr_blocks = extracted_data.blocks
    cur_text_title: str = TITLE
    cur_figure_title = TITLE
    non_text_cache: list[Component] = []
    cur_text_co = Component(type="text", title=cur_text_title)
    for i, block in enumerate(ocr_blocks):
        location = Location(bbox=block.bbox, page=block.page_id)
        if block.is_title():
            cur_text_title = block.content
            # 如果之前的组件有内容, 将其添加到body中
            if cur_text_co.title != TITLE or cur_text_co.data != "":
                co_pack.body.append(cur_text_co)
            co_pack.body.extend(non_text_cache)
            # 按照当前标题初始化一个新的文本组件
            non_text_cache.clear()
            cur_text_co = Component(type="text", title=cur_text_title)

        elif block.is_figure():
            cur_figure_co = Component(
                type=block.label, title=cur_figure_title, location=[location]
            )
            # 标题在图的上方
            if i > 0 and ocr_blocks[i - 1].is_figure_title():
                cur_figure_title = ocr_blocks[i - 1].content
                cur_figure_co.location.append(location)
            # 标题在图的下方
            elif i + 1 < len(ocr_blocks) and ocr_blocks[i + 1].is_figure_title():
                cur_figure_title = ocr_blocks[i + 1].content
                cur_figure_co.location.append(location)
            # 没有标题
            else:
                cur_figure_title = TITLE

            cur_figure_co.title = cur_figure_title
            non_text_cache.append(cur_figure_co)

        elif block.is_figure_title():
            logger.warning(
                f"Figure title [{block.block_id}: {block.content}] is not assigned to any figure."
            )

        elif block.is_header():
            if block.page_id not in header:
                header[block.page_id] = Component(
                    type="header", data=block.content, location=[location]
                )
            else:
                header[block.page_id].data += f" {block.content}"
                header[block.page_id].location.append(location)

        elif block.is_footer():
            if block.page_id not in footer:
                footer[block.page_id] = Component(
                    type="footer", data=block.content, location=[location]
                )
            else:
                footer[block.page_id].data += f" {block.content}"
                footer[block.page_id].location.append(location)

        elif block.is_number():
            if block.page_id not in number:
                number[block.page_id] = Component(
                    type="number", data=block.content, location=[location]
                )
            else:
                number[block.page_id].data += f" {block.content}"
                number[block.page_id].location.append(location)

        elif block.is_aside():
            if block.page_id not in aside:
                aside[block.page_id] = Component(
                    type="aside_text", data=block.content, location=[location]
                )
            else:
                aside[block.page_id].data += f" {block.content}"
                aside[block.page_id].location.append(location)

        else:
            cur_text_co.data += "\n\n" + block.content
            cur_text_co.location.append(location)

    if cur_text_co.title != TITLE or cur_text_co.data != "":
        co_pack.body.append(cur_text_co)

    co_pack.body.extend(non_text_cache)

    for co in co_pack.body:
        if co.type in ["image", "chart", "table"]:
            title, metadata, data = information_enrichment(extracted_data.source, co)
            co.title = title if co.title == TITLE else co.title
            co.metadata = metadata
            co.data = data if co.data == "" else co.data

    return co_pack
