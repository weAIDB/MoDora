from __future__ import annotations
import logging
from typing import Optional
from modora.core.settings import Settings
from modora.core.interfaces.ocr import OCRClient
from modora.core.infra.ocr.factory import OCRFactory

_ocr_client: Optional[OCRClient] = None


def ensure_ocr_model_loaded(settings: Settings, logger: logging.Logger) -> None:
    """
    确保 OCR 模型已加载。
    如果尚未初始化，则根据设置创建 OCR 客户端实例。
    """
    global _ocr_client
    if _ocr_client is not None:
        return

    try:
        _ocr_client = OCRFactory.create(settings)
        logger.info(f"OCR 模型 ({settings.ocr_model}) 已就绪")
    except Exception as e:
        logger.error(f"加载 OCR 模型失败: {e}")
        raise


def get_ocr_model() -> Optional[OCRClient]:
    """获取已加载的 OCR 客户端实例。"""
    return _ocr_client
