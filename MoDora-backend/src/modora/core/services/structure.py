from __future__ import annotations

import logging

from modora.core.domain import (
    TITLE,
    Component,
    Location,
    ComponentPack,
    OcrExtractResponse,
)


class StructureAnalyzer:
    """Analyzes flat OCR results into a structured ComponentPack."""

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
                # If the previous component has content, add it to the body
                if cur_text_co.title != TITLE or cur_text_co.data != "":
                    co_pack.body.append(cur_text_co)
                co_pack.body.extend(non_text_cache)
                # Initialize a new text component according to the current title
                non_text_cache.clear()
                cur_text_co = Component(type="text", title=cur_text_title)
                # The title's own bbox must also be added to the location of the new component
                cur_text_co.location.append(location)
                # Also add the title content to data to ensure check_node text contains the title
                cur_text_co.data = cur_text_title

            elif block.is_figure():
                cur_figure_co = Component(
                    type=block.label, title=cur_figure_title, location=[location]
                )
                # Title is above the figure
                if i > 0 and ocr_blocks[i - 1].is_figure_title():
                    cur_figure_title = ocr_blocks[i - 1].content
                    cur_figure_co.location.append(location)
                # Title is below the figure
                elif i + 1 < len(ocr_blocks) and ocr_blocks[i + 1].is_figure_title():
                    cur_figure_title = ocr_blocks[i + 1].content
                    cur_figure_co.location.append(location)
                # No title
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
