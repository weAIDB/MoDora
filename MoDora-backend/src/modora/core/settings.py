from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

"""System configuration module.

This module provides application configuration management functions, supporting
configuration loading from environment variables and JSON configuration files.
Configuration loading priority: Environment variables > Configuration files > Default values.

Main features:
    - Type-safe configuration value conversion.
    - Multi-source configuration merging (environment variables, configuration files).
"""


def _coerce_bool(val: Any, default: bool = False) -> bool:
    """Coerces a value from environment variables or configuration files into a boolean.

    Args:
        val: The value to be converted.
        default: The default value to return if val is None.

    Returns:
        bool: The converted boolean value.
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
class ModelInstance:
    type: str
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    port: int | None = None
    device: str | None = None


@dataclass(frozen=True)
class Settings:
    """Application configuration class.

    Attributes:
        env: Running environment (dev/test/prod).
        service_name: Service identifier (service/lab).
        log_level: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL).
        log_format: Log format (text/json).
        log_to_file: Whether to enable file logging.
        log_dir: Log directory path, default location is used if None.
        api_base: API service base URL.
        api_key: API authentication key.
        api_port: API service port.

    Note:
        All fields have default values to ensure the configuration object is always valid.
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
    exp_dir: str | None = None
    chroma_persist_path: str | None = None

    api_base: str | None = None
    api_key: str | None = None
    api_port: int = 8005

    embedding_api_base: str | None = None
    embedding_api_key: str | None = None
    embedding_model_name: str | None = None

    rerank_api_base: str | None = None
    rerank_api_key: str | None = None
    rerank_model_name: str | None = None

    model_instances: dict[str, ModelInstance] = field(default_factory=dict)

    llm_local_startup_timeout_s: float = 600.0

    ocr_model: str = "ppstructure"
    ocr_device: str = "gpu:7"
    ocr_lang: str = "en"
    ocr_layout_unclip_ratio: float | tuple[float, float] = 1.2
    ocr_text_recognition_batch_size: int = 8
    ocr_use_table_recognition: bool = True
    ocr_use_doc_unwarping: bool = False

    enable_vector_search: bool = True

    def resolve_model_instance(self, inst_id: str) -> ModelInstance | None:
        """Resolves a model instance by its ID."""
        return self.model_instances.get(inst_id)

    @staticmethod
    def load(config_path: str | None = None) -> "Settings":
        """Loads configuration from multiple sources.

        Sets environment variables to optimize the running environment:
        1. TOKENIZERS_PARALLELISM: Set to false to avoid multiprocessing warnings and deadlocks.
        2. PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK: Set to True to skip model source connection checks for PaddlePDX.
        """
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

        cfg_path = (config_path or os.getenv("MODORA_CONFIG") or "").strip()
        cfg: dict[str, Any] = {}

        if not cfg_path:
            backend_root = Path(__file__).resolve().parents[3]
            project_root = backend_root.parent

            possible_paths = [
                project_root / "local.json",
                backend_root / "configs" / "local.json",
            ]

            for p in possible_paths:
                if p.exists():
                    cfg_path = str(p)
                    break

            if not cfg_path:
                cfg_path = str(project_root / "local.json")

        if os.path.exists(cfg_path):
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
        chroma_persist_path = _clean_str(pick("chroma_persist_path", None))

        api_base = _clean_str(pick("api_base", None))
        api_key = _clean_str(pick("api_key", None))
        api_port = int(pick("api_port", 8005))

        embedding_api_base = _clean_str(pick("embedding_api_base", None))
        embedding_api_key = _clean_str(pick("embedding_api_key", None))
        embedding_model_name = _clean_str(
            pick("embedding_model_name", "text-embedding-3-large")
        )
        rerank_api_base = _clean_str(pick("rerank_api_base", None))
        rerank_api_key = _clean_str(pick("rerank_api_key", None))
        rerank_model_name = _clean_str(pick("rerank_model_name", None))

        model_instances_raw = _coerce_json(pick("model_instances", None))
        model_instances: dict[str, ModelInstance] = {}
        if isinstance(model_instances_raw, dict):
            for name, payload in model_instances_raw.items():
                if not isinstance(payload, dict):
                    continue
                inst_type = _clean_str(payload.get("type", None)) or ""
                inst_type = inst_type.lower()
                if inst_type not in {"local", "remote"}:
                    continue
                model = _clean_str(payload.get("model", None))
                base_url = _clean_str(
                    payload.get("base_url", None) or payload.get("baseUrl", None)
                )
                api_key_val = _clean_str(
                    payload.get("api_key", None) or payload.get("apiKey", None)
                )
                key = _clean_str(name) or str(name)
                port_val = payload.get("port", None)
                try:
                    port = int(port_val) if port_val is not None else None
                except Exception:
                    port = None
                device = _clean_str(
                    payload.get("device", None)
                    or payload.get("cuda_visible_devices", None)
                )
                model_instances[key] = ModelInstance(
                    type=inst_type,
                    model=model,
                    base_url=base_url,
                    api_key=api_key_val,
                    port=port,
                    device=device,
                )

        llm_local_startup_timeout_s = float(pick("llm_local_startup_timeout_s", 600.0))

        ocr_model = _clean_str(pick("ocr_model", "ppstructure"))
        ocr_device = _clean_str(pick("ocr_device", "gpu:7")) or "gpu:7"
        ocr_lang = _clean_str(pick("ocr_lang", "en"))
        ocr_layout_unclip_ratio = _coerce_float_or_pair(
            pick("ocr_layout_unclip_ratio", 1.2), default=1.2
        )
        ocr_text_recognition_batch_size = int(
            pick("ocr_text_recognition_batch_size", 8)
        )
        ocr_use_table_recognition = _coerce_bool(
            pick("ocr_use_table_recognition", True), default=True
        )
        ocr_use_doc_unwarping = _coerce_bool(
            pick("ocr_use_doc_unwarping", False), default=False
        )
        enable_vector_search = _coerce_bool(
            pick("enable_vector_search", True), default=True
        )

        repo_root = Path(__file__).resolve().parents[4]
        default_docs = str(repo_root / "datasets" / "MMDA")
        default_cache = str(repo_root / "cache")

        def _resolve_path(val: str | None, default: str) -> str:
            raw = _clean_str(val) or default
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = repo_root / p
            return str(p)

        docs_dir = _resolve_path(pick("docs_dir", default_docs), default_docs)
        cache_dir = _resolve_path(pick("cache_dir", default_cache), default_cache)
        exp_dir = _resolve_path(pick("exp_dir", cache_dir), cache_dir)

        return Settings(
            env=env,
            service_name=service_name,
            log_level=log_level,
            log_format=log_format,
            log_to_file=log_to_file,
            log_dir=log_dir,
            docs_dir=docs_dir,
            cache_dir=cache_dir,
            exp_dir=exp_dir,
            chroma_persist_path=chroma_persist_path,
            api_base=api_base,
            api_key=api_key,
            api_port=api_port,
            embedding_api_base=embedding_api_base,
            embedding_api_key=embedding_api_key,
            embedding_model_name=embedding_model_name,
            rerank_api_base=rerank_api_base,
            rerank_api_key=rerank_api_key,
            rerank_model_name=rerank_model_name,
            model_instances=model_instances,
            llm_local_startup_timeout_s=llm_local_startup_timeout_s,
            ocr_model=ocr_model,
            ocr_device=ocr_device,
            ocr_lang=ocr_lang,
            ocr_layout_unclip_ratio=ocr_layout_unclip_ratio,
            ocr_text_recognition_batch_size=ocr_text_recognition_batch_size,
            ocr_use_table_recognition=ocr_use_table_recognition,
            ocr_use_doc_unwarping=ocr_use_doc_unwarping,
            enable_vector_search=enable_vector_search,
        )
