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
    "ocr",
    "pipelines",
    "schemaVersion",
}

MODULE_KEYS = {
    "enrichment",
    "levelGenerator",
    "metadataGenerator",
    "retriever",
    "qaService",
}

LEGACY_MODEL_KEY_TO_MODULE = {
    "qaModel": "qaService",
    "treeModel": "levelGenerator",
}


def normalize_ui_settings(payload: dict[str, Any] | None) -> dict[str, Any]:
    """标准化前端 settings 载荷，同时兼容 v1/v2。"""
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

    if isinstance(normalized.get("ocr"), dict):
        provider = normalized["ocr"].get("provider")
        if provider is not None:
            provider = str(provider).strip()
            normalized["ocr"] = {"provider": provider} if provider else {}
        else:
            normalized["ocr"] = {}
    elif "ocr" in normalized:
        normalized.pop("ocr", None)

    pipelines = normalized.get("pipelines")
    if isinstance(pipelines, dict):
        clean_pipelines: dict[str, dict[str, str]] = {}
        for module, value in pipelines.items():
            if module not in MODULE_KEYS or not isinstance(value, dict):
                continue
            item: dict[str, str] = {}
            mode = str(value.get("mode") or "").strip().lower()
            if mode in {"local", "remote"}:
                item["mode"] = mode
            for field in ("model", "baseUrl", "apiKey"):
                raw = value.get(field)
                if raw is None:
                    continue
                clean = str(raw).strip()
                if clean:
                    item[field] = clean
            clean_pipelines[module] = item
        normalized["pipelines"] = clean_pipelines
    elif "pipelines" in normalized:
        normalized.pop("pipelines", None)

    return normalized


def _legacy_pipeline_fallback(cfg: dict[str, Any], module_key: str) -> dict[str, str]:
    fallback: dict[str, str] = {}
    mode = cfg.get("selectedMode")
    if mode in {"local", "remote"}:
        fallback["mode"] = mode

    if module_key in {"levelGenerator", "metadataGenerator"}:
        model_name = cfg.get("treeModel") or cfg.get("qaModel")
    else:
        model_name = cfg.get("qaModel") or cfg.get("treeModel")
    if model_name:
        fallback["model"] = str(model_name).strip()

    if cfg.get("baseUrl"):
        fallback["baseUrl"] = str(cfg["baseUrl"]).strip()
    if cfg.get("apiKey"):
        fallback["apiKey"] = str(cfg["apiKey"]).strip()
    return fallback


def get_pipeline_config(
    payload: dict[str, Any] | None,
    module_key: str,
) -> dict[str, str]:
    """获取指定模块的配置，优先 v2 pipelines，其次回退 v1。"""
    cfg = normalize_ui_settings(payload)
    if module_key not in MODULE_KEYS:
        return {}

    pipelines = cfg.get("pipelines")
    if isinstance(pipelines, dict) and isinstance(pipelines.get(module_key), dict):
        return dict(pipelines[module_key])
    return _legacy_pipeline_fallback(cfg, module_key)


def settings_from_ui_payload(
    base: Settings,
    payload: dict[str, Any] | None,
    *,
    model_key: str | None = None,
    module_key: str | None = None,
) -> tuple[Settings, str | None, dict[str, Any]]:
    """从前端 settings 载荷构造后端 Settings 覆盖值。"""
    cfg = normalize_ui_settings(payload)
    overrides: dict[str, Any] = {}

    ocr = cfg.get("ocr")
    if isinstance(ocr, dict) and ocr.get("provider"):
        overrides["ocr_model"] = ocr["provider"]
    elif cfg.get("layoutModel"):
        overrides["ocr_model"] = cfg["layoutModel"]

    resolved_module = module_key
    if resolved_module is None and model_key:
        resolved_module = LEGACY_MODEL_KEY_TO_MODULE.get(model_key)

    pipeline_cfg = (
        get_pipeline_config(cfg, resolved_module) if resolved_module else {}
    )
    selected_mode = pipeline_cfg.get("mode") or cfg.get("selectedMode")

    base_url = pipeline_cfg.get("baseUrl") or cfg.get("baseUrl")
    api_key = pipeline_cfg.get("apiKey") or cfg.get("apiKey")
    if base_url:
        overrides["api_base"] = base_url
    if api_key:
        overrides["api_key"] = api_key

    model_name = pipeline_cfg.get("model")
    if not model_name and model_key and cfg.get(model_key):
        model_name = str(cfg[model_key]).strip()
    if not model_name:
        model_name = str(cfg.get("qaModel") or cfg.get("treeModel") or "").strip() or None

    if model_name and selected_mode != "local":
        overrides["api_model"] = model_name

    settings = replace(base, **overrides) if overrides else base
    return settings, selected_mode, cfg


def resolve_llm_mode(config: dict[str, Any] | None, key: str) -> str | None:
    """从配置字典中解析 LLM 模式。"""
    module = key
    if key in LEGACY_MODEL_KEY_TO_MODULE:
        module = LEGACY_MODEL_KEY_TO_MODULE[key]
    pipeline_cfg = get_pipeline_config(config, module)
    if pipeline_cfg.get("mode") in {"local", "remote"}:
        return pipeline_cfg["mode"]
    cfg = normalize_ui_settings(config)
    val = str(cfg.get("selectedMode") or "").lower()
    return val if val in {"local", "remote"} else None


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
