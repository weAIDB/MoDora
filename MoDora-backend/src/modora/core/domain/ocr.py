from __future__ import annotations

from pydantic import BaseModel


class OCRBlock(BaseModel):
    """A single block of structured OCR.

    Attributes:
        page_id: Page number starting from 1.
        bbox: [x0, y0, x1, y1], aligned with the PDF coordinate system (used for subsequent cropping/rendering).
    """

    page_id: int
    block_id: int
    bbox: list[float]
    label: str
    content: str

    def is_title(self) -> bool:
        """Title type block (triggers new chapter splitting)."""
        return self.label in ["title", "paragraph_title", "doc_title"]

    def is_figure(self) -> bool:
        """Non-text block (used for enrichment: image/chart/table)."""
        return self.label in ["image", "chart", "table"]

    def is_figure_title(self) -> bool:
        """Figure title or visual footnote (may belong to figure/table caption)."""
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
    """OCR output.

    Attributes:
        source: Input PDF path.
        blocks: Structured OCR results, each block containing page number, bounding box, label, and content.
    """

    source: str
    blocks: list[OCRBlock]
