from __future__ import annotations

import logging

from modora.core.domain.component import TITLE, Component, Location, ComponentPack
from modora.core.domain.ocr import OcrExtractResponse


class StructureAnalyzer:
    """负责将 OCR 扁平结果分析为结构化的 ComponentPack。"""

    def analyze(
        self, extracted_data: OcrExtractResponse, logger: logging.Logger
    ) -> ComponentPack:
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

        return co_pack
