from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

from modora.core.settings import Settings

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


def ensure_llm_local_loaded(settings: Settings, logger: Any) -> None:
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

    if not settings.llm_local_model:
        logger.info("local llm disabled", extra={"llm_local_model": None})
        return

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

    bases: list[tuple[str, int, str, str | None]] = []
    for inst in instances:
        host = (getattr(inst, "host", None) or "127.0.0.1").strip() or "127.0.0.1"
        port = int(
            getattr(inst, "port", settings.llm_local_port) or settings.llm_local_port
        )
        url_host = "localhost" if host in {"0.0.0.0"} else host
        base = f"http://{url_host}:{port}/v1"
        cuda_visible_devices = getattr(inst, "cuda_visible_devices", None)
        bases.append((host, port, base, cuda_visible_devices))

    for host, port, base, cuda_visible_devices in bases:
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
            settings.llm_local_model,
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
            },
        )
        _llm_local_procs[key] = subprocess.Popen(cmd, env=env)

    deadline = time.time() + float(settings.llm_local_startup_timeout_s)
    last: str | None = None
    pending: set[tuple[str, int]] = {(h, p) for h, p, _, _ in bases}
    while time.time() < deadline:
        for host, port, base, _ in bases:
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
                extra={"base_urls": [b for _, _, b, _ in bases]},
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
