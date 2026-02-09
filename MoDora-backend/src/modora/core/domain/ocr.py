from __future__ import annotations

from pydantic import BaseModel


class OCRBlock(BaseModel):
    """
    结构化 OCR 的单个 block。

    Attributes:
        page_id: 从 1 开始的页号
        bbox: [x0, y0, x1, y1]，与 PDF 坐标系对齐（用于后续裁剪/渲染）
    """

    page_id: int
    block_id: int
    bbox: list[float]
    label: str
    content: str

    def is_title(self) -> bool:
        """标题类 block（会触发新章节切分）。"""
        return self.label in ["title", "paragraph_title", "doc_title"]

    def is_figure(self) -> bool:
        """非文本类 block（用于 enrichment：image/chart/table）。"""
        return self.label in ["image", "chart", "table"]

    def is_figure_title(self) -> bool:
        """图片标题或视觉脚注（可能属于图/表的说明文字）。"""
        return self.label in ["figure_title", "vision_footnote"]

    def is_header(self) -> bool:
        return self.label == "header"

    def is_footer(self) -> bool:
        return self.label == "footer"

    def is_number(self) -> bool:
        return self.label == "number"

    def is_aside(self) -> bool:
        return self.label == "aside_text"


class OcrExtractResponse(BaseModel):
    """
    OCR 输出.
    Attributes:
        source: 输入的 pdf 路径.
        blocks: 结构化 OCR 结果，每个 block 包含页号、边界框、标签和内容。
    """

    source: str
    blocks: list[OCRBlock]
