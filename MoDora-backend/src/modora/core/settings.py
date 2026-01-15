from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

""" 
系统配置模块

本模块提供应用程序配置管理功能，支持从环境变量和JSON配置文件加载配置。
配置加载优先级：环境变量 > 配置文件 > 默认值

主要功能：
    - 类型安全的配置值转换
    - 多源配置合并（环境变量、配置文件）

"""


def _coerce_bool(val: Any, default: bool = False) -> bool:
    """
    将来自环境变量或者配置文件的值转为 bool
    Args:
        val: 待转换的值
        default: 默认值，当 val 为 None 时返回

    Returns:
        转换后的 bool 值
    """
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    val_str = str(val).strip().lower()
    if val_str in {"1", "true", "t", "yes", "y", "on"}:
        return True
    elif val_str in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def _read_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj if isinstance(obj, dict) else {}


def _clean_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


@dataclass(frozen=True)
class Settings:
    """应用程序配置类

    配置字段说明：
        - env: 运行环境 (dev/test/prod)
        - service_name: 服务标识符 (service/lab)
        - log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        - log_format: 日志格式 (text/json)
        - log_to_file: 是否启用文件日志
        - log_dir: 日志目录路径，为None时使用默认位置
        - api_base: API服务基础URL
        - api_key: API认证密钥

    注意：所有字段都有默认值，确保配置对象始终有效。
    """

    env: str = "dev"
    service_name: str = "modora-backend"

    log_level: str = "INFO"  # DEBUG/INFO/WARNING/ERROR/CRITICAL
    log_format: str = "text"  # text/json
    log_to_file: bool = False
    log_dir: str | None = None

    api_base: str | None = None
    api_key: str | None = None

    @staticmethod
    def load(config_path: str | None = None) -> "Settings":
        cfg_path = (config_path or os.getenv("MODORA_CONFIG") or "").strip()
        cfg: dict[str, Any] = {}
        if cfg_path and os.path.exists(cfg_path):
            cfg = _read_json(cfg_path)

        def pick(key: str, default: Any = None) -> Any:
            env_key = f"MODORA_{key.upper()}"
            if env_key in os.environ:
                return os.environ[env_key]
            if key in cfg:
                return cfg[key]
            return default

        env = _clean_str(pick("env", "dev"))
        service_name = _clean_str(pick("service_name", "modora-backend"))

        log_level = _clean_str(pick("log_level", "INFO")).upper()
        log_format = _clean_str(pick("log_format", "text")).lower()
        if log_format not in {"text", "json"}:
            log_format = "text"
        log_to_file = _coerce_bool(pick("log_to_file", False))
        log_dir = _clean_str(pick("log_dir", None))

        api_base = _clean_str(pick("api_base", None))
        api_key = _clean_str(pick("api_key", None))

        return Settings(
            env=env,
            service_name=service_name,
            log_level=log_level,
            log_format=log_format,
            log_to_file=log_to_file,
            log_dir=log_dir,
            api_base=api_base,
            api_key=api_key,
        )


if __name__ == "__main__":
    """
    配置加载示例

    方式1：使用默认配置
        settings = Settings.load()

    方式2：指定配置文件
        settings = Settings.load("/path/to/config.json")
    或者
        export MODORA_CONFIG=/path/to/config.json

    方式3：通过环境变量
        export MODORA_ENV=prod
        export MODORA_LOG_LEVEL=DEBUG
        settings = Settings.load()

    方式4：混合使用
        export MODORA_API_KEY=your-key
        settings = Settings.load("config.json")
    """
    # 演示如何使用
    settings = Settings.load()
    print(f"Environment: {settings.env}")
    print(f"Log Level: {settings.log_level}")
    print(f"API Base: {settings.api_base or 'Not set'}")
