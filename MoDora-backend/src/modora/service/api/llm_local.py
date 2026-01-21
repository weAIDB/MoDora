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
    """
    发送 HTTP GET 请求，用于健康检查。
    捕获各类异常（包括超时），确保不抛出异常中断主流程。
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
    """
    确保本地 LLM 服务（lmdeploy）已启动。

    逻辑：
    1. 检查配置，如果未启用 llm_local_model 则直接返回。
    2. 解析 llm_local_instances 配置，确定需要启动的实例列表。
    3. 对每个实例：
       - 检查是否已有进程在运行且健康（通过 /v1/models 接口）。
       - 如果端口未被占用且无响应，则启动新的 lmdeploy 子进程。
    4. 轮询等待所有实例启动就绪（直到超时）。
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
            "starting local llm server",
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
