from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from modora.core.settings import Settings, ModelInstance
from modora.core.utils.config import (
    MODULE_KEYS,
    load_ui_settings_from_config,
    normalize_ui_settings,
)

_llm_local_procs: dict[tuple[str, int], subprocess.Popen] = {}


def _http_get(url: str, timeout_s: float) -> tuple[int, str]:
    """Send HTTP GET request for health check.

    Catches various exceptions (including timeouts) to ensure main process is not interrupted.
    """
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read(4096)
            return int(getattr(resp, "status", 200)), body.decode(
                "utf-8", errors="replace"
            )
    except urllib.error.HTTPError as e:
        body = (e.read(4096) or b"").decode("utf-8", errors="replace")
        return int(e.code), body
    except urllib.error.URLError as e:
        return 0, str(e)
    except (TimeoutError, socket.timeout):
        return 0, "timeout"


def _parse_base_url(base_url: str) -> tuple[str | None, int | None]:
    if not base_url:
        return None, None
    val = base_url.strip()
    if not val:
        return None, None
    if "://" not in val:
        val = "http://" + val
    parsed = urlparse(val)
    return parsed.hostname, parsed.port


def _resolve_model_path(model: str) -> str:
    if not model:
        return model
    p = Path(model)
    if p.is_absolute() and p.exists():
        return str(p)
    cwd_path = Path.cwd() / p
    if cwd_path.exists():
        return str(cwd_path)
    backend_root = Path(__file__).resolve().parents[5]
    backend_path = backend_root / p
    if backend_path.exists():
        return str(backend_path)
    repo_root = Path(__file__).resolve().parents[6]
    repo_path = repo_root / p
    if repo_path.exists():
        return str(repo_path)
    return model


def _selected_model_instance_ids(
    settings: Settings, config_path: str | None = None
) -> list[str]:
    ui_settings = load_ui_settings_from_config(config_path)
    normalized = normalize_ui_settings(ui_settings)
    instances = settings.model_instances or {}
    default_instance_id = next(iter(instances.keys()), None)
    selected: list[str] = []
    pipelines = normalized.get("pipelines")
    if isinstance(pipelines, dict):
        for key in MODULE_KEYS:
            item = pipelines.get(key)
            if isinstance(item, dict):
                model_instance = item.get("modelInstance")
                if isinstance(model_instance, str) and model_instance.strip():
                    selected.append(model_instance.strip())
                    continue
            if default_instance_id:
                selected.append(default_instance_id)
    elif default_instance_id:
        selected = [default_instance_id]

    seen: set[str] = set()
    deduped: list[str] = []
    for item in selected:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _resolve_local_entries(
    settings: Settings, *, config_path: str | None = None, force: bool = False
) -> list[tuple[str, int, str | None, str | None]]:
    local_entries: list[tuple[str, int, str | None, str | None]] = []
    instances: list[ModelInstance] = []
    if settings.model_instances:
        if force:
            for inst in settings.model_instances.values():
                if inst.type == "local" and inst.model:
                    instances.append(inst)
        else:
            for inst_id in _selected_model_instance_ids(settings, config_path):
                inst = settings.resolve_model_instance(inst_id)
                if inst and inst.type == "local" and inst.model:
                    instances.append(inst)

        for inst in instances:
            host = "127.0.0.1"
            port = inst.port
            if inst.base_url and not port:
                parsed_host, parsed_port = _parse_base_url(inst.base_url)
                if parsed_host:
                    host = parsed_host
                if parsed_port:
                    port = parsed_port
            if not port:
                port = settings.llm_local_port
            local_entries.append(
                (host, int(port), _resolve_model_path(inst.model), inst.device)
            )

    return local_entries


def ensure_llm_local_loaded(
    settings: Settings,
    logger: Any,
    *,
    config_path: str | None = None,
    force: bool = False,
) -> None:
    """Ensure local LLM service (lmdeploy) is started.

    Logic:
    1. Check configuration. If llm_local_model is not enabled, return immediately.
    2. Parse llm_local_instances configuration to determine the list of instances to start.
    3. For each instance:
       - Check if a process is already running and healthy (via /v1/models interface).
       - If the port is not occupied and there's no response, start a new lmdeploy child process.
    4. Poll and wait for all instances to be ready (until timeout).
    """
    global _llm_local_procs

    local_entries = _resolve_local_entries(
        settings, config_path=config_path, force=force
    )

    if not local_entries and settings.model_instances and not force:
        logger.info("local llm disabled", extra={"llm_local_model": None})
        return

    if not local_entries and not settings.llm_local_model:
        logger.info("local llm disabled", extra={"llm_local_model": None})
        return

    bases: list[tuple[str, int, str, str | None, str]] = []
    if local_entries:
        for host, port, model, device in local_entries:
            url_host = "localhost" if host in {"0.0.0.0"} else host
            base = f"http://{url_host}:{port}/v1"
            bases.append((host, port, base, device, model))
    else:
        instances = list(getattr(settings, "llm_local_instances", ()) or ())
        if not instances:
            instances = [
                type(
                    "_TmpInst",
                    (),
                    {
                        "host": "127.0.0.1",
                        "port": int(settings.llm_local_port),
                        "cuda_visible_devices": settings.llm_local_cuda_visible_devices,
                    },
                )()
            ]

        for inst in instances:
            host = (getattr(inst, "host", None) or "127.0.0.1").strip() or "127.0.0.1"
            port = int(
                getattr(inst, "port", settings.llm_local_port)
                or settings.llm_local_port
            )
            url_host = "localhost" if host in {"0.0.0.0"} else host
            base = f"http://{url_host}:{port}/v1"
            cuda_visible_devices = getattr(inst, "cuda_visible_devices", None)
            model_path = _resolve_model_path(settings.llm_local_model)
            bases.append((host, port, base, cuda_visible_devices, model_path))

    for host, port, base, cuda_visible_devices, model in bases:
        key = (host, port)
        proc = _llm_local_procs.get(key)
        if proc is not None and proc.poll() is None:
            continue

        code, _ = _http_get(base + "/models", timeout_s=0.2)
        if code == 200:
            continue

        env = os.environ.copy()
        if cuda_visible_devices:
            env["CUDA_VISIBLE_DEVICES"] = str(cuda_visible_devices)

        cmd = [
            "lmdeploy",
            "serve",
            "api_server",
            model,
            "--server-port",
            str(port),
        ]
        logger.info(
            "starting local llm server (lmdeploy)",
            extra={
                "cmd": " ".join(cmd),
                "cuda_visible": cuda_visible_devices,
                "host": host,
                "port": port,
                "model": model,
            },
        )
        _llm_local_procs[key] = subprocess.Popen(cmd, env=env)

    deadline = time.time() + float(settings.llm_local_startup_timeout_s)
    last: str | None = None
    pending: set[tuple[str, int]] = {(h, p) for h, p, _, _, _ in bases}
    while time.time() < deadline:
        for host, port, base, _, _ in bases:
            key = (host, port)
            if key not in pending:
                continue

            proc = _llm_local_procs.get(key)
            if proc is not None and proc.poll() is not None:
                raise RuntimeError(
                    f"local llm server exited during startup: {host}:{port}"
                )

            code, body = _http_get(base + "/models", timeout_s=1.0)
            if code == 200:
                pending.remove(key)
                continue

            last = f"{host}:{port} status={code}, body={body[:200]}"

        if not pending:
            logger.info(
                "local llm servers started",
                extra={"base_urls": [b for _, _, b, _, _ in bases]},
            )
            return
        time.sleep(0.5)

    raise RuntimeError(
        f"local llm servers not started in {settings.llm_local_startup_timeout_s}s: {last}"
    )


def shutdown_llm_local() -> None:
    global _llm_local_procs

    if not _llm_local_procs:
        return

    for key, proc in list(_llm_local_procs.items()):
        if proc.poll() is not None:
            _llm_local_procs.pop(key, None)
            continue
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        finally:
            _llm_local_procs.pop(key, None)
