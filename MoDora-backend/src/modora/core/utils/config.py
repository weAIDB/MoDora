from __future__ import annotations

from typing import Any
from dataclasses import replace
from modora.core.settings import LlmLocalInstance, Settings

ALLOWED_UI_SETTINGS_KEYS = {
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


def normalize_ui_settings(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Standardize frontend settings payload.

    Args:
        payload (dict[str, Any] | None): The settings payload from the frontend.

    Returns:
        dict[str, Any]: The normalized settings dictionary.
    """
    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, Any] = {}
    for key in ALLOWED_UI_SETTINGS_KEYS:
        if key in payload:
            normalized[key] = payload[key]

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
            model_instance = value.get("modelInstance")
            if isinstance(model_instance, str) and model_instance.strip():
                item["modelInstance"] = model_instance.strip()
            clean_pipelines[module] = item
        normalized["pipelines"] = clean_pipelines
    elif "pipelines" in normalized:
        normalized.pop("pipelines", None)

    return normalized


def get_pipeline_config(
    payload: dict[str, Any] | None,
    module_key: str,
) -> dict[str, str]:
    """Get configuration for the specified module.

    Args:
        payload (dict[str, Any] | None): The settings payload.
        module_key (str): The key for the module (e.g., 'retriever', 'qaService').

    Returns:
        dict[str, str]: The configuration dictionary for the module.
    """
    cfg = normalize_ui_settings(payload)
    if module_key not in MODULE_KEYS:
        return {}

    pipelines = cfg.get("pipelines")
    if isinstance(pipelines, dict) and isinstance(pipelines.get(module_key), dict):
        return dict(pipelines[module_key])
    return {}


def settings_from_ui_payload(
    base: Settings,
    payload: dict[str, Any] | None,
    *,
    module_key: str | None = None,
) -> tuple[Settings, str | None, dict[str, Any]]:
    """Construct backend Settings overrides from frontend settings payload.

    Args:
        base (Settings): The base Settings instance.
        payload (dict[str, Any] | None): The settings payload from the UI.
        module_key (str | None): Module key for pipeline config.

    Returns:
        tuple[Settings, str | None, dict[str, Any]]: A tuple containing the
            updated Settings, the selected mode, and the normalized config.
    """
    cfg = normalize_ui_settings(payload)
    overrides: dict[str, Any] = {}

    ocr = cfg.get("ocr")
    if isinstance(ocr, dict) and ocr.get("provider"):
        overrides["ocr_model"] = ocr["provider"]

    pipeline_cfg = get_pipeline_config(cfg, module_key) if module_key else {}
    model_instance_id = pipeline_cfg.get("modelInstance")
    model_instance = base.resolve_model_instance(model_instance_id)
    selected_mode = model_instance.type if model_instance else None

    if model_instance:
        if model_instance.type == "remote":
            base_url = model_instance.base_url
            api_key = model_instance.api_key
            model_name = model_instance.model
            if base_url:
                overrides["api_base"] = base_url
            if api_key:
                overrides["api_key"] = api_key
            if model_name:
                overrides["api_model"] = model_name
        else:
            base_url = model_instance.base_url
            api_key = model_instance.api_key
            model_name = model_instance.model
            port = model_instance.port
            device = model_instance.device
            if base_url:
                overrides["llm_local_base_url"] = base_url
            elif port:
                overrides["llm_local_base_url"] = f"http://127.0.0.1:{port}/v1"
            if api_key:
                overrides["llm_local_api_key"] = api_key
            if model_name:
                overrides["llm_local_model"] = model_name
            if port or device:
                overrides["llm_local_instances"] = (
                    LlmLocalInstance(
                        host="127.0.0.1",
                        port=port or base.llm_local_port,
                        cuda_visible_devices=device,
                    ),
                )

    settings = replace(base, **overrides) if overrides else base
    return settings, selected_mode, cfg
