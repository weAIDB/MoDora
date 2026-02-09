from __future__ import annotations

from typing import List

import fitz

from modora.core.domain.ocr import OCRBlock, OcrExtractResponse


def extract_pdf_blocks(file_path: str) -> OcrExtractResponse:
    doc = fitz.open(file_path)
    blocks: List[OCRBlock] = []
    block_id = 0
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            page_height = page.rect.height or 1.0
            raw_blocks = page.get_text("blocks") or []
            for item in raw_blocks:
                if len(item) < 5:
                    continue
                x0, y0, x1, y1, text = item[0], item[1], item[2], item[3], item[4]
                text = (text or "").strip()
                if not text:
                    continue

                # Heuristic: short text near top = title
                word_count = len(text.split())
                is_title = word_count <= 12 and y0 <= 0.2 * page_height
                label = "title" if is_title else "text"

                blocks.append(
                    OCRBlock(
                        page_id=page_index + 1,
                        block_id=block_id,
                        bbox=[float(x0), float(y0), float(x1), float(y1)],
                        label=label,
                        content=text,
                    )
                )
                block_id += 1
    finally:
        doc.close()

    return OcrExtractResponse(source=f"file:{file_path}", blocks=blocks)
