from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException

from modora.core.settings import ModelInstance, Settings
from modora.core.utils.config import (
    MODULE_KEYS,
    normalize_ui_settings,
    save_ui_settings_to_config,
)

router = APIRouter(tags=["models"])


def _fallback_instances(settings: Settings) -> dict[str, ModelInstance]:
    instances: dict[str, ModelInstance] = {}
    if settings.llm_local_model or settings.llm_local_base_url:
        instances["local-default"] = ModelInstance(
            type="local",
            model=settings.llm_local_model,
            base_url=settings.llm_local_base_url,
            api_key=settings.llm_local_api_key,
            port=settings.llm_local_port,
            device=settings.llm_local_cuda_visible_devices,
        )
    if settings.api_base or settings.api_key or settings.api_model:
        instances["remote-default"] = ModelInstance(
            type="remote",
            model=settings.api_model,
            base_url=settings.api_base,
            api_key=settings.api_key,
        )
    return instances


def _load_ui_settings(settings: Settings) -> dict[str, object]:
    cfg_path = (os.getenv("MODORA_CONFIG") or "").strip()
    raw_settings: dict[str, object] | None = None
    if cfg_path:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("ui_settings"), dict):
                raw_settings = data.get("ui_settings")
        except Exception:
            raw_settings = None

    normalized = normalize_ui_settings(raw_settings)
    instances = settings.model_instances or _fallback_instances(settings)
    default_instance_id = next(iter(instances.keys()), None)

    pipelines: dict[str, dict[str, str]] = {}
    for key in MODULE_KEYS:
        pipeline: dict[str, str] = {}
        if default_instance_id:
            pipeline["modelInstance"] = default_instance_id
        if isinstance(normalized.get("pipelines"), dict):
            item = normalized["pipelines"].get(key)
            if isinstance(item, dict):
                model_instance = item.get("modelInstance")
                if isinstance(model_instance, str) and model_instance.strip():
                    pipeline["modelInstance"] = model_instance.strip()
        pipelines[key] = pipeline

    ocr_provider = settings.ocr_model
    if isinstance(normalized.get("ocr"), dict):
        provider = normalized["ocr"].get("provider")
        if isinstance(provider, str) and provider.strip():
            ocr_provider = provider.strip()

    return {
        "schemaVersion": 3,
        "ocr": {"provider": ocr_provider},
        "pipelines": pipelines,
    }


@router.get("/models/instances")
def list_model_instances():
    settings = Settings.load()
    instances = settings.model_instances or _fallback_instances(settings)
    payload = []
    for key, inst in instances.items():
        payload.append(
            {
                "id": key,
                "type": inst.type,
                "model": inst.model,
                "base_url": inst.base_url,
                "port": inst.port,
                "device": inst.device,
            }
        )
    return {"instances": payload}


@router.get("/settings/ui")
def get_ui_settings():
    settings = Settings.load()
    ui_settings = _load_ui_settings(settings)
    return {"settings": ui_settings}


@router.post("/settings/ui")
def update_ui_settings(payload: dict[str, object]):
    raw_settings = payload.get("settings") if isinstance(payload, dict) else None
    try:
        saved = save_ui_settings_to_config(raw_settings)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"settings": saved}
