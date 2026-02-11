from __future__ import annotations
import logging
from threading import Lock
from typing import Optional
from modora.core.settings import Settings
from modora.core.interfaces.ocr import OCRClient
from modora.core.infra.ocr.factory import OCRFactory

_ocr_clients: dict[tuple, OCRClient] = {}
_default_ocr_key: tuple | None = None
_ocr_lock = Lock()


def _normalize_ratio(value):
    if isinstance(value, (list, tuple)):
        return tuple(float(v) for v in value)
    try:
        return float(value)
    except Exception:
        return value


def _ocr_settings_key(settings: Settings) -> tuple:
    return (
        settings.ocr_model,
        settings.ocr_device,
        settings.ocr_lang,
        _normalize_ratio(settings.ocr_layout_unclip_ratio),
        int(settings.ocr_text_recognition_batch_size),
        bool(settings.ocr_use_table_recognition),
        bool(settings.ocr_use_doc_unwarping),
    )


def ensure_ocr_model_loaded(settings: Settings, logger: logging.Logger) -> None:
    """
    确保 OCR 模型已加载。
    如果尚未初始化，则根据设置创建 OCR 客户端实例。
    """
    get_ocr_model(settings=settings, logger=logger, create_if_missing=True)


def get_ocr_model(
    settings: Settings | None = None,
    logger: logging.Logger | None = None,
    *,
    create_if_missing: bool = False,
) -> Optional[OCRClient]:
    """获取 OCR 客户端实例。

    - 未传 settings: 返回默认实例（应用启动时加载的实例）。
    - 传入 settings 且 create_if_missing=True: 按配置获取或创建实例（带缓存复用）。
    """
    global _default_ocr_key

    with _ocr_lock:
        if settings is None:
            if _default_ocr_key is None:
                return None
            return _ocr_clients.get(_default_ocr_key)

        key = _ocr_settings_key(settings)
        existing = _ocr_clients.get(key)
        if existing is not None:
            if _default_ocr_key is None:
                _default_ocr_key = key
            return existing

        if not create_if_missing:
            return None

        try:
            client = OCRFactory.create(settings)
            _ocr_clients[key] = client
            if _default_ocr_key is None:
                _default_ocr_key = key
            if logger is not None:
                logger.info(
                    "OCR 模型已就绪",
                    extra={
                        "ocr_model": settings.ocr_model,
                        "ocr_device": settings.ocr_device,
                    },
                )
            return client
        except Exception as e:
            if logger is not None:
                logger.error(f"加载 OCR 模型失败: {e}")
            raise
