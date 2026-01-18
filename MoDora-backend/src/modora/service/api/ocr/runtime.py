from __future__ import annotations

from typing import Any

from paddleocr import PPStructureV3

from modora.core.settings import Settings

_ocr_model: Any | None = None

def ensure_ocr_model_loaded(settings: Settings, logger) -> None:
    global _ocr_model
    if _ocr_model is not None:
        return

    device = (settings.ocr_device or "").strip() or "gpu:6"
    _ocr_model = PPStructureV3(
        device=device,
        use_table_recognition=bool(settings.ocr_use_table_recognition),
        use_doc_unwarping=bool(settings.ocr_use_doc_unwarping),
        lang=settings.ocr_lang or "en",
        layout_unclip_ratio=float(settings.ocr_layout_unclip_ratio),
    )
    logger.info(
        "ocr model ready",
        extra={
            "device": device,
            "lang": settings.ocr_lang or "en",
            "layout_unclip_ratio": float(settings.ocr_layout_unclip_ratio),
        },
    )

def get_ocr_model() -> Any | None:
    return _ocr_model