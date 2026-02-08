from __future__ import annotations

from typing import Any

from modora.core.settings import Settings

_ocr_model: Any | None = None


def ensure_ocr_model_loaded(settings: Settings, logger) -> None:
    global _ocr_model
    if _ocr_model is not None:
        return

    device = (settings.ocr_device or "").strip() or "gpu:6"
    kwargs: dict[str, Any] = {
        "device": device,
        "use_table_recognition": bool(settings.ocr_use_table_recognition),
        "use_doc_unwarping": bool(settings.ocr_use_doc_unwarping),
    }

    # Try PPStructureV3 first (PaddleOCR 3.x)
    try:
        from paddleocr import PPStructureV3  # type: ignore
        _ocr_model = PPStructureV3(**kwargs)
        logger.info(
            "ocr model ready (PPStructureV3)",
            extra={"device": device},
        )
        return
    except Exception as e:
        logger.warning(f"PPStructureV3 init failed: {e}")

    # Fallback to PPStructure (PaddleOCR 2.x)
    try:
        from paddleocr import PPStructure  # type: ignore
        _ocr_model = PPStructure(**kwargs)
        logger.info(
            "ocr model ready (PPStructure)",
            extra={"device": device},
        )
        return
    except Exception as e:
        logger.warning(f"PPStructure init failed: {e}")
        _ocr_model = None
        return
    logger.info(
        "ocr model ready",
        extra={
            "device": device,
            "lang": settings.ocr_lang or "en",
            "layout_unclip_ratio": settings.ocr_layout_unclip_ratio,
        },
    )


def get_ocr_model() -> Any | None:
    return _ocr_model
