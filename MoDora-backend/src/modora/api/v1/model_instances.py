from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from modora.api.auth import require_current_user
from modora.core.auth.service import AuthUser
from modora.core.persistence.user_preferences import (
    add_user_model_instance,
    delete_user_model_instance,
    effective_settings_for_user,
    get_user_ui_settings,
    save_user_ui_settings,
)
from modora.core.settings import ModelInstance, Settings
from modora.core.utils.config import (
    MODULE_KEYS,
    normalize_ui_settings,
)

router = APIRouter(tags=["models"])


class CreateModelInstanceRequest(BaseModel):
    model_name: str
    base_url: str
    api_key: str | None = None


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


def _load_ui_settings(settings: Settings, *, user_id: str | None = None) -> dict[str, object]:
    cfg_path = (os.getenv("MODORA_CONFIG") or "").strip()
    raw_settings: dict[str, object] | None = None
    if user_id:
        raw_settings = get_user_ui_settings(settings, user_id=user_id)
    if cfg_path and not user_id:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("ui_settings"), dict):
                raw_settings = raw_settings or data.get("ui_settings")
        except Exception:
            raw_settings = raw_settings or None

    normalized = normalize_ui_settings(raw_settings)
    instances = settings.model_instances or (_fallback_instances(settings) if not user_id else {})
    default_instance_id = next(iter(instances.keys()), None) if not user_id else None

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


def _instance_in_use(ui_settings: dict[str, object], instance_id: str) -> bool:
    pipelines = ui_settings.get("pipelines")
    if not isinstance(pipelines, dict):
        return False
    for value in pipelines.values():
        if not isinstance(value, dict):
            continue
        if value.get("modelInstance") == instance_id:
            return True
    return False


@router.get("/models/instances")
def list_model_instances(user: AuthUser = Depends(require_current_user)):
    settings = effective_settings_for_user(Settings.load(), user_id=user.id)
    instances = settings.model_instances
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
def get_ui_settings(user: AuthUser = Depends(require_current_user)):
    settings = effective_settings_for_user(Settings.load(), user_id=user.id)
    ui_settings = _load_ui_settings(settings, user_id=user.id)
    return {"settings": ui_settings}


@router.post("/settings/ui")
def update_ui_settings(
    payload: dict[str, object],
    user: AuthUser = Depends(require_current_user),
):
    raw_settings = payload.get("settings") if isinstance(payload, dict) else None
    try:
        saved = save_user_ui_settings(
            Settings.load(),
            user_id=user.id,
            payload=normalize_ui_settings(raw_settings),
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"settings": saved}


@router.post("/models/instances", status_code=201)
def create_model_instance(
    payload: CreateModelInstanceRequest,
    user: AuthUser = Depends(require_current_user),
):
    model_name = payload.model_name.strip()
    base_url = payload.base_url.strip()
    api_key = (payload.api_key or "").strip() or None

    if not model_name:
        raise HTTPException(status_code=400, detail="model_name is required")
    if not base_url:
        raise HTTPException(status_code=400, detail="base_url is required")

    settings = Settings.load()
    try:
        instance = add_user_model_instance(
            settings,
            user_id=user.id,
            instance_name=model_name,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "instance": {
            "id": model_name,
            "type": instance.type,
            "model": instance.model,
            "base_url": instance.base_url,
            "port": instance.port,
            "device": instance.device,
        }
    }


@router.delete("/models/instances/{instance_id}", status_code=204)
def delete_model_instance(
    instance_id: str,
    user: AuthUser = Depends(require_current_user),
):
    settings = Settings.load()
    ui_settings = _load_ui_settings(
        effective_settings_for_user(settings, user_id=user.id),
        user_id=user.id,
    )
    if _instance_in_use(ui_settings, instance_id):
        raise HTTPException(
            status_code=400,
            detail="model instance is still referenced by current settings",
        )

    deleted = delete_user_model_instance(
        settings,
        user_id=user.id,
        instance_name=instance_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="model instance not found")
    return None
