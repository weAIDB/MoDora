from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
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


def _coerce_json(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        if (s.startswith("{") and s.endswith("}")) or (
            s.startswith("[") and s.endswith("]")
        ):
            try:
                return json.loads(s)
            except Exception:
                return None
    return None


def _coerce_float_or_pair(
    val: Any, default: float | tuple[float, float] | None
) -> float | tuple[float, float] | None:
    if val is None:
        return default

    if isinstance(val, (int, float)):
        return float(val)

    if isinstance(val, (list, tuple)) and len(val) == 2:
        try:
            return (float(val[0]), float(val[1]))
        except Exception:
            return default

    s = str(val).strip()
    if not s:
        return default

    if s.lower() in {"none", "null"}:
        return None

    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = json.loads(s)
        except Exception:
            parsed = None
        if isinstance(parsed, list) and len(parsed) == 2:
            try:
                return (float(parsed[0]), float(parsed[1]))
            except Exception:
                return default

    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        parts = [p for p in parts if p]
        if len(parts) == 2:
            try:
                return (float(parts[0]), float(parts[1]))
            except Exception:
                return default

    try:
        return float(s)
    except Exception:
        return default


@dataclass(frozen=True)
class LlmLocalInstance:
    host: str = "127.0.0.1"
    port: int = 9001
    cuda_visible_devices: str | None = None


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

    # Data paths
    docs_dir: str | None = None
    cache_dir: str | None = None

    api_base: str | None = None
    api_key: str | None = None
    api_model: str | None = None

    llm_local_model: str | None = None
    llm_local_base_url: str | None = None
    llm_local_api_key: str = "local"
    llm_local_port: int = 9001
    llm_local_cuda_visible_devices: str | None = None
    llm_local_startup_timeout_s: float = 600.0
    llm_local_instances: tuple[LlmLocalInstance, ...] = ()

    ocr_model: str = "ppstructure"
    ocr_device: str = "gpu:6"
    ocr_lang: str = "en"
    ocr_layout_unclip_ratio: float | tuple[float, float] | None = 1.1
    ocr_use_table_recognition: bool = True
    ocr_use_doc_unwarping: bool = False

    @staticmethod
    def load(config_path: str | None = None) -> "Settings":
        """从多个来源加载配置
        
        设置环境变量以优化运行环境：
        1. TOKENIZERS_PARALLELISM: 设置为 false 以避免多进程警告和死锁。
        2. PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK: 设置为 True 以跳过 PaddlePDX 的模型源连接检查。
        """
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

        cfg_path = (config_path or os.getenv("MODORA_CONFIG") or "").strip()
        cfg: dict[str, Any] = {}
        if cfg_path and os.path.exists(cfg_path):
            cfg = _read_json(cfg_path)

        def pick(key: str, default: Any = None) -> Any:
            env_key = f"MODORA_{key.upper()}"
            if env_key in os.environ:
                return os.environ[env_key]
            # Backwards/compat: allow standard OpenAI env var for api_key
            if key == "api_key" and "OPENAI_API_KEY" in os.environ:
                return os.environ["OPENAI_API_KEY"]
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
        api_model = _clean_str(pick("api_model", None))

        llm_local_model = _clean_str(pick("llm_local_model", None))
        llm_local_base_url = _clean_str(pick("llm_local_base_url", None))
        llm_local_api_key = _clean_str(pick("llm_local_api_key", "local"))
        llm_local_port = int(pick("llm_local_port", 9001))
        llm_local_cuda_visible_devices = _clean_str(
            pick("llm_local_cuda_visible_devices", None)
        )
        llm_local_startup_timeout_s = float(pick("llm_local_startup_timeout_s", 600.0))

        llm_local_instances_raw = _coerce_json(pick("llm_local_instances", None))
        llm_local_instances: tuple[LlmLocalInstance, ...] = ()
        if isinstance(llm_local_instances_raw, list):
            inst_list: list[LlmLocalInstance] = []
            for it in llm_local_instances_raw:
                if not isinstance(it, dict):
                    continue
                port_raw = it.get("port", None)
                if port_raw is None:
                    continue
                try:
                    port = int(port_raw)
                except Exception:
                    continue
                host = _clean_str(it.get("host", None)) or "127.0.0.1"
                cuda_visible_devices = _clean_str(it.get("cuda_visible_devices", None))
                inst_list.append(
                    LlmLocalInstance(
                        host=host, port=port, cuda_visible_devices=cuda_visible_devices
                    )
                )
            llm_local_instances = tuple(inst_list)

        if not llm_local_instances and llm_local_model:
            llm_local_instances = (
                LlmLocalInstance(
                    host="127.0.0.1",
                    port=llm_local_port,
                    cuda_visible_devices=llm_local_cuda_visible_devices,
                ),
            )

        ocr_model = _clean_str(pick("ocr_model", "ppstructure"))
        ocr_device = _clean_str(pick("ocr_device", "gpu:6")) or "gpu:6"
        ocr_lang = _clean_str(pick("ocr_lang", "en"))
        ocr_layout_unclip_ratio = _coerce_float_or_pair(
            pick("ocr_layout_unclip_ratio", 0.5), default=0.5
        )
        ocr_use_table_recognition = _coerce_bool(
            pick("ocr_use_table_recognition", True), default=True
        )
        ocr_use_doc_unwarping = _coerce_bool(
            pick("ocr_use_doc_unwarping", False), default=False
        )

        repo_root = Path(__file__).resolve().parents[4]
        default_docs = str(repo_root / "datasets" / "MMDA")
        default_cache = str(repo_root / "MoDora-backend" / "cache")
        docs_dir = _clean_str(pick("docs_dir", default_docs)) or default_docs
        cache_dir = _clean_str(pick("cache_dir", default_cache)) or default_cache

        return Settings(
            env=env,
            service_name=service_name,
            log_level=log_level,
            log_format=log_format,
            log_to_file=log_to_file,
            log_dir=log_dir,
            docs_dir=docs_dir,
            cache_dir=cache_dir,
            api_base=api_base,
            api_key=api_key,
            api_model=api_model,
            llm_local_model=llm_local_model,
            llm_local_base_url=llm_local_base_url,
            llm_local_api_key=llm_local_api_key,
            llm_local_port=llm_local_port,
            llm_local_cuda_visible_devices=llm_local_cuda_visible_devices,
            llm_local_startup_timeout_s=llm_local_startup_timeout_s,
            llm_local_instances=llm_local_instances,
            ocr_model=ocr_model,
            ocr_device=ocr_device,
            ocr_lang=ocr_lang,
            ocr_layout_unclip_ratio=ocr_layout_unclip_ratio,
            ocr_use_table_recognition=ocr_use_table_recognition,
            ocr_use_doc_unwarping=ocr_use_doc_unwarping,
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
