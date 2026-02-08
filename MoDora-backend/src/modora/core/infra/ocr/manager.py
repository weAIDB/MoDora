from __future__ import annotations
import logging
from typing import Optional
from modora.core.settings import Settings
from modora.core.interfaces.ocr import OCRClient
from modora.core.infra.ocr.factory import OCRFactory

_ocr_client: Optional[OCRClient] = None

def ensure_ocr_model_loaded(settings: Settings, logger: logging.Logger) -> None:
    global _ocr_client
    if _ocr_client is not None:
        return

    try:
        _ocr_client = OCRFactory.create(settings)
        logger.info(f"OCR model ({settings.ocr_model}) ready")
    except Exception as e:
        logger.error(f"Failed to load OCR model: {e}")
        raise

def get_ocr_model() -> Optional[OCRClient]:
    return _ocr_client
