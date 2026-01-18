from __future__ import annotations

import base64
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modora.service.api.ocr.runtime import get_ocr_model

router = APIRouter(prefix="/ocr", tags=["ocr"])


class OCRExtractRequest(BaseModel):
    image_base64: str


class OCRBlock(BaseModel):
    id: int
    bbox: list[float]
    type: str
    text: str


class OcrExtractResponse(BaseModel):
    blocks: list[OCRBlock]


def _strip_data_url_prefix(s: str) -> str:
    if s.startswith("data:") and "," in s:
        s = s.split(",", maxsplit=1)[1]
    return s


@router.post("/extract", response_model=OcrExtractResponse)
def ocr_extract(request: OCRExtractRequest) -> OcrExtractResponse:
    model = get_ocr_model()
    if model is None:
        raise HTTPException(status_code=503, detail="ocr model not loaded")

    s = _strip_data_url_prefix(request.image_base64)
    try:
        raw = base64.b64decode(s, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid base64 image")

    import cv2
    import numpy as np

    buf = np.frombuffer(raw, dtype=np.uint8)
    img_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="invalid image")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    it = model.predict_iter(img_rgb)
    try:
        out = next(it)
    except StopIteration:
        return OcrExtractResponse(blocks=[])

    regions: Any = None
    if isinstance(out, dict):
        regions = out.get("parsing_res_list")
        if regions is None:
            regions = out.get("region_det_res")
        if regions is None and isinstance(out.get("res"), dict):
            res = out["res"]
            regions = res.get("parsing_res_list") or res.get("region_det_res")
    elif isinstance(out, tuple) and out:
        regions = out[0]

    if isinstance(regions, tuple) and regions:
        regions = regions[0]
    if not isinstance(regions, list):
        regions = []

    blocks: list[OCRBlock] = []
    for i, region in enumerate(regions):
        if isinstance(region, dict):
            bbox = region.get("block_bbox") or region.get("bbox")
            label = (
                region.get("block_label")
                or region.get("type")
                or region.get("label")
                or region.get("layout_label")
                or "text"
            )
            text_val = (
                region.get("block_content")
                or region.get("text")
                or region.get("rec_text")
                or region.get("content")
                or ""
            )
            block_id = region.get("block_id", region.get("id", i))
        else:
            bbox = getattr(region, "bbox", None) or getattr(region, "layout_bbox", None)
            label = (
                getattr(region, "type", None)
                or getattr(region, "label", None)
                or getattr(region, "layout_label", None)
                or "text"
            )
            text_val = (
                getattr(region, "text", None)
                or getattr(region, "rec_text", None)
                or getattr(region, "content", None)
            )
            if not text_val:
                res_val = getattr(region, "res", None)
                rec_texts: list[str] = []
                if res_val:
                    for line in res_val:
                        if isinstance(line, dict) and isinstance(line.get("text"), str):
                            rec_texts.append(line["text"])
                        elif isinstance(line, (tuple, list)) and line and isinstance(line[0], str):
                            rec_texts.append(line[0])
                text_val = "\n".join(rec_texts)

            block_id = getattr(region, "block_id", None)
            if block_id is None:
                block_id = getattr(region, "id", i)

        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue

        try:
            bid = int(block_id)
        except Exception:
            bid = i

        blocks.append(
            OCRBlock(
                id=bid,
                bbox=[float(x) for x in bbox],
                type=str(label).lower(),
                text=str(text_val or ""),
            )
        )

    return OcrExtractResponse(blocks=blocks)