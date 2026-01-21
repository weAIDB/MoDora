from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modora.core.domain.ocr import OCRBlock, OcrExtractResponse
from modora.service.api.ocr.runtime import get_ocr_model

router = APIRouter(prefix="/ocr", tags=["ocr"])


class OCRExtractRequest(BaseModel):
    """OCR 输入：支持 base64 图片或本地图片路径（二选一）。"""

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
    """将输入图片 bytes 解码为 RGB ndarray，供 PPStructureV3 使用。"""
    buf = np.frombuffer(raw, dtype=np.uint8)
    img_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="invalid image")
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def _blocks_from_parsing_res_list(res_list: Any, *, page_id: int) -> list[OCRBlock]:
    """将 PPStructureV3 的 parsing_res_list 归一化为 OCRBlock 列表。"""
    blocks: list[OCRBlock] = []
    for res in res_list:
        blocks.append(
            OCRBlock(
                page_id=int(page_id),
                block_id=res.index,
                # 这里做一次 0.5 缩放，用于将模型坐标对齐到 PDF 坐标系。
                bbox=[0.5 * x for x in res.bbox],
                label=res.label,
                content=res.content,
            )
        )
    return blocks


@router.post("/extract", response_model=OcrExtractResponse)
def ocr_extract(request: OCRExtractRequest) -> OcrExtractResponse:
    """
    通用 OCR 提取接口（支持单图 Base64 或本地文件）。
    主要用于调试或单张图片处理。
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
        out = next(it)
    except StopIteration:
        return OcrExtractResponse(source=source, blocks=[])

    regions = out.get("parsing_res_list")
    blocks = _blocks_from_parsing_res_list(regions, page_id=1)
    return OcrExtractResponse(source=source, blocks=blocks)


@router.post("/extract_pdf", response_model=OcrExtractResponse)
def ocr_extract_pdf(request: OCRExtractPdfRequest) -> OcrExtractResponse:
    """
    PDF OCR 提取接口。
    逐页处理 PDF，返回所有页面的 Block 列表。
    """
    model = get_ocr_model()
    if model is None:
        raise HTTPException(status_code=503, detail="ocr model not loaded")

    pdf_input, source = request.resolve_pdf_input()

    pdf_blocks: list[OCRBlock] = []
    for idx, out in enumerate(model.predict_iter(pdf_input)):
        res_list = out.get("parsing_res_list")
        page_blocks = _blocks_from_parsing_res_list(res_list, page_id=idx + 1)
        pdf_blocks.extend(page_blocks)

    return OcrExtractResponse(source=source, blocks=pdf_blocks)
