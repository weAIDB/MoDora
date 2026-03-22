from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from modora.core.persistence.db import connect_db
from modora.core.settings import ModelInstance, Settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _ensure_row(settings: Settings, *, user_id: str) -> None:
    with connect_db(settings) as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (user_id, updated_at)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, _now_iso()),
        )


def get_user_ui_settings(settings: Settings, *, user_id: str) -> dict[str, Any] | None:
    _ensure_row(settings, user_id=user_id)
    with connect_db(settings) as conn:
        row = conn.execute(
            "SELECT ui_settings_json FROM user_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    value = _coerce_object(row["ui_settings_json"])
    return value or None


def save_user_ui_settings(
    settings: Settings,
    *,
    user_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_row(settings, user_id=user_id)
    encoded = json.dumps(payload, ensure_ascii=False)
    with connect_db(settings) as conn:
        conn.execute(
            """
            UPDATE user_preferences
            SET ui_settings_json = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (encoded, _now_iso(), user_id),
        )
    return payload


def get_user_model_instances(
    settings: Settings,
    *,
    user_id: str,
) -> dict[str, ModelInstance]:
    _ensure_row(settings, user_id=user_id)
    with connect_db(settings) as conn:
        row = conn.execute(
            "SELECT model_instances_json FROM user_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return {}

    raw = _coerce_object(row["model_instances_json"])
    instances: dict[str, ModelInstance] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        model_name = str(value.get("model") or "").strip()
        base_url = str(value.get("base_url") or "").strip()
        api_key = str(value.get("api_key") or "").strip()
        if not model_name or not base_url:
            continue
        instances[key] = ModelInstance(
            type="remote",
            model=model_name,
            base_url=base_url,
            api_key=api_key or None,
        )
    return instances


def save_user_model_instances(
    settings: Settings,
    *,
    user_id: str,
    model_instances: dict[str, ModelInstance],
) -> dict[str, ModelInstance]:
    _ensure_row(settings, user_id=user_id)
    payload = {
        key: {
            "type": inst.type,
            "model": inst.model,
            "base_url": inst.base_url,
            "api_key": inst.api_key,
            "port": inst.port,
            "device": inst.device,
        }
        for key, inst in model_instances.items()
    }
    encoded = json.dumps(payload, ensure_ascii=False)
    with connect_db(settings) as conn:
        conn.execute(
            """
            UPDATE user_preferences
            SET model_instances_json = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (encoded, _now_iso(), user_id),
        )
    return model_instances


def add_user_model_instance(
    settings: Settings,
    *,
    user_id: str,
    instance_name: str,
    model_name: str,
    base_url: str,
    api_key: str | None,
) -> ModelInstance:
    current = get_user_model_instances(settings, user_id=user_id)
    if instance_name in current:
        raise ValueError(f"model instance '{instance_name}' already exists")

    instance = ModelInstance(
        type="remote",
        model=model_name,
        base_url=base_url,
        api_key=(api_key or "").strip() or None,
    )
    current[instance_name] = instance
    save_user_model_instances(settings, user_id=user_id, model_instances=current)
    return instance


def delete_user_model_instance(
    settings: Settings,
    *,
    user_id: str,
    instance_name: str,
) -> bool:
    current = get_user_model_instances(settings, user_id=user_id)
    if instance_name not in current:
        return False
    current.pop(instance_name, None)
    save_user_model_instances(settings, user_id=user_id, model_instances=current)
    return True


def effective_settings_for_user(
    settings: Settings,
    *,
    user_id: str | None,
) -> Settings:
    if not user_id:
        return settings
    user_instances = get_user_model_instances(settings, user_id=user_id)
    return replace(
        settings,
        model_instances=dict(user_instances),
        api_base=None,
        api_key=None,
    )
