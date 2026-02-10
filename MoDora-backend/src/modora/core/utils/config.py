from __future__ import annotations

from typing import Any
from dataclasses import replace
from modora.core.settings import Settings

def resolve_llm_mode(config: dict[str, Any] | None, key: str) -> str | None:
    """从配置字典中解析 LLM 模式。"""
    if not config:
        return None
    val = str(config.get(key) or "").lower()
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
