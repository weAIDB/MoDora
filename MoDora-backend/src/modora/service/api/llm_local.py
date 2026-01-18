from __future__ import annotations

import os
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

from modora.core.settings import Settings

_llm_local_proc: subprocess.Popen | None = None


def _http_get(url: str, timeout_s: float) -> tuple[int, str]:
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


def ensure_llm_local_loaded(settings: Settings, logger: Any) -> None:
    global _llm_local_proc

    if not settings.llm_local_model:
        logger.info("local llm disabled", extra={"llm_local_model": None})
        return

    if _llm_local_proc is not None and _llm_local_proc.poll() is None:
        return

    env = os.environ.copy()
    if settings.llm_local_cuda_visible_devices:
        env["CUDA_VISIBLE_DEVICES"] = settings.llm_local_cuda_visible_devices

    cmd = [
        "lmdeploy",
        "serve",
        "api_server",
        settings.llm_local_model,
        "--server-port",
        str(settings.llm_local_port),
    ]
    logger.info(
        "starting local llm server",
        extra={
            "cmd": " ".join(cmd),
            "cuda_visible": settings.llm_local_cuda_visible_devices,
        },
    )

    _llm_local_proc = subprocess.Popen(cmd, env=env)

    base = f"http://localhost:{settings.llm_local_port}/v1"
    deadline = time.time() + float(settings.llm_local_startup_timeout_s)
    last: str | None = None

    while time.time() < deadline:
        if _llm_local_proc.poll() is not None:
            raise RuntimeError("local llm server exited during startup")

        code, body = _http_get(base + "/models", timeout_s=1.0)
        if code == 200:
            logger.info("local llm server started", extra={"base_url": base})
            return

        last = f"status={code}, body={body[:200]}"
        time.sleep(0.5)

    raise RuntimeError(
        f"local llm server not started in {settings.llm_local_startup_timeout_s}s: {last}"
    )


def shutdown_llm_local() -> None:
    global _llm_local_proc

    if _llm_local_proc is None:
        return
    if _llm_local_proc.poll() is not None:
        _llm_local_proc = None
        return

    _llm_local_proc.terminate()
    try:
        _llm_local_proc.wait(timeout=5)
    except Exception:
        _llm_local_proc.kill()
    finally:
        _llm_local_proc = None