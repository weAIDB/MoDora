from __future__ import annotations

from typing import Any
from dataclasses import replace
from modora.core.settings import Settings

ALLOWED_UI_SETTINGS_KEYS = {
    "apiKey",
    "baseUrl",
    "selectedMode",
    "layoutModel",
    "qaModel",
    "treeModel",
}


def normalize_ui_settings(payload: dict[str, Any] | None) -> dict[str, Any]:
    """标准化前端 settings 载荷，仅保留白名单字段。"""
    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, Any] = {}
    for key in ALLOWED_UI_SETTINGS_KEYS:
        if key in payload:
            normalized[key] = payload[key]

    mode = str(normalized.get("selectedMode") or "").lower()
    if mode in {"local", "remote"}:
        normalized["selectedMode"] = mode
    elif "selectedMode" in normalized:
        normalized.pop("selectedMode", None)

    for key in ("apiKey", "baseUrl", "layoutModel", "qaModel", "treeModel"):
        if key in normalized and normalized[key] is not None:
            normalized[key] = str(normalized[key]).strip()

    return normalized


def settings_from_ui_payload(
    base: Settings,
    payload: dict[str, Any] | None,
    *,
    model_key: str | None = None,
) -> tuple[Settings, str | None, dict[str, Any]]:
    """从前端 settings 载荷构造后端 Settings 覆盖值。"""
    cfg = normalize_ui_settings(payload)
    overrides: dict[str, Any] = {}

    if cfg.get("apiKey"):
        overrides["api_key"] = cfg["apiKey"]
    if cfg.get("baseUrl"):
        overrides["api_base"] = cfg["baseUrl"]
    if cfg.get("layoutModel"):
        overrides["ocr_model"] = cfg["layoutModel"]

    selected_mode = cfg.get("selectedMode")
    model_name: str | None = None
    if model_key and cfg.get(model_key):
        model_name = cfg[model_key]
    elif cfg.get("qaModel"):
        model_name = cfg["qaModel"]
    elif cfg.get("treeModel"):
        model_name = cfg["treeModel"]

    if model_name and selected_mode != "local":
        overrides["api_model"] = model_name

    settings = replace(base, **overrides) if overrides else base
    return settings, selected_mode, cfg


def resolve_llm_mode(config: dict[str, Any] | None, key: str) -> str | None:
    """从配置字典中解析 LLM 模式。"""
    cfg = normalize_ui_settings(config)
    if not cfg:
        return None
    val = str(cfg.get(key) or "").lower()
    if "local" in val:
        return "local"
    if val:
        return "remote"
    return None


def settings_with_overrides(
    base: Settings, overrides: dict[str, Any] | None, *, api_model: str | None = None
) -> Settings:
    """使用覆盖参数创建新的 Settings 实例。"""
    payload: dict[str, Any] = {}
    if overrides:
        if overrides.get("apiKey"):
            payload["api_key"] = overrides.get("apiKey")
        if overrides.get("baseUrl"):
            payload["api_base"] = overrides.get("baseUrl")
    if api_model:
        payload["api_model"] = api_model
    return replace(base, **payload) if payload else base
