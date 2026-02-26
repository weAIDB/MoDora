from __future__ import annotations

import base64
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modora.core.domain.ocr import OCRBlock, OcrExtractResponse
from modora.core.infra.ocr.manager import get_ocr_model

router = APIRouter(prefix="/ocr", tags=["ocr"])


class OCRExtractRequest(BaseModel):
    """OCR input request.

    Supports either base64 image data or a local image path.
    """

    image_base64: str | None = None
    file_path: str | None = None

    def load_image_bytes(self) -> bytes:
        if self.image_base64 and self.file_path:
            raise HTTPException(
                status_code=400, detail="only one of image_base64/file_path is allowed"
            )

        if self.image_base64:
            s = _strip_data_url_prefix(self.image_base64)
            try:
                return base64.b64decode(s, validate=True)
            except Exception:
                raise HTTPException(status_code=400, detail="invalid base64 image")

        if self.file_path:
            p = Path(self.file_path)
            if not p.is_file():
                raise HTTPException(status_code=400, detail="file_path not found")
            if p.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                raise HTTPException(
                    status_code=400, detail="file_path must be .png/.jpg/.jpeg"
                )
            return p.read_bytes()

        raise HTTPException(
            status_code=400, detail="image_base64 or file_path required"
        )


class OCRExtractPdfRequest(BaseModel):
    file_path: str

    def resolve_pdf_input(self) -> tuple[str, str]:
        p = Path(self.file_path)
        if not p.is_file():
            raise HTTPException(status_code=400, detail="file_path not found")
        if p.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="file_path must be .pdf")
        return str(p), f"file:{p}"


def _strip_data_url_prefix(s: str) -> str:
    if s.startswith("data:") and "," in s:
        s = s.split(",", maxsplit=1)[1]
    return s


def _decode_image_bytes_to_rgb(raw: bytes):
    """Decode input image bytes to RGB ndarray for PPStructureV3.

    Args:
        raw: Raw image bytes.

    Returns:
        np.ndarray: Image in RGB format.
    """
    buf = np.frombuffer(raw, dtype=np.uint8)
    img_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="invalid image")
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


@router.post("/extract", response_model=OcrExtractResponse)
def ocr_extract(request: OCRExtractRequest) -> OcrExtractResponse:
    """General OCR extraction interface.

    Supports single image via Base64 or local file. Mainly used for
    debugging or single image processing.

    Args:
        request: OCR extraction request.

    Returns:
        OcrExtractResponse: Extracted OCR blocks.
    """
    model = get_ocr_model()
    if model is None:
        raise HTTPException(status_code=503, detail="ocr model not loaded")

    raw = request.load_image_bytes()
    img_rgb = _decode_image_bytes_to_rgb(raw)

    source = (
        "image_base64"
        if request.image_base64
        else (f"file:{request.file_path}" if request.file_path else "-")
    )

    it = model.predict_iter(img_rgb)
    try:
        blocks = next(it)
    except StopIteration:
        return OcrExtractResponse(source=source, blocks=[])

    return OcrExtractResponse(source=source, blocks=blocks)


@router.post("/extract_pdf", response_model=OcrExtractResponse)
def ocr_extract_pdf(request: OCRExtractPdfRequest) -> OcrExtractResponse:
    """PDF OCR extraction interface.

    Processes PDF page by page and returns a list of blocks for all pages.

    Args:
        request: PDF OCR extraction request.

    Returns:
        OcrExtractResponse: Extracted OCR blocks from the PDF.
    """
    model = get_ocr_model()
    if model is None:
        raise HTTPException(status_code=503, detail="ocr model not loaded")

    pdf_input, source = request.resolve_pdf_input()

    pdf_blocks: list[OCRBlock] = []
    for page_blocks in model.predict_iter(pdf_input):
        pdf_blocks.extend(page_blocks)

    return OcrExtractResponse(source=source, blocks=pdf_blocks)
