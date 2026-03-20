#!/usr/bin/env python3

from __future__ import annotations

import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


DEFAULT_BASE_URL = "https://api.modora.pro"
SKILL_HEADERS = {"X-Modora-Client": "skill"}


def get_base_url() -> str:
    return os.environ.get("MODORA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def print_err(*args: object) -> None:
    print(*args, file=sys.stderr)


def require_remote_credential_ack(flag: bool) -> None:
    if flag:
        return
    if os.environ.get("MODORA_ALLOW_REMOTE_CREDENTIALS", "").strip() == "1":
        return
    raise SystemExit(
        "This skill sends settings.json, including model endpoints and API credentials, "
        "to the remote MoDora service. Re-run with --allow-remote-credentials "
        "or set MODORA_ALLOW_REMOTE_CREDENTIALS=1 if you trust that server."
    )


def ensure_absolute_file(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        raise SystemExit("Please use an absolute file path.")
    if not path.is_file():
        raise SystemExit(f"File not found: {path}")
    return path


def load_settings_file(path_str: str | None = None) -> dict:
    settings_path = path_str or os.environ.get("MODORA_SETTINGS_FILE")
    if not settings_path:
        raise SystemExit(
            "Skill access requires a user-owned settings file. "
            "Pass --settings-file or set MODORA_SETTINGS_FILE. "
            "The script will not fall back to server defaults. "
            "The settings must contain the user's own model credentials and multimodal model configuration."
        )

    path = Path(settings_path)
    if not path.is_file():
        raise SystemExit(f"Settings file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Failed to read settings file: {path}") from exc

    if not isinstance(data, dict):
        raise SystemExit("Settings file must contain a JSON object.")

    return data


def parse_json_bytes(data: bytes) -> object:
    return json.loads(data.decode("utf-8"))


def request_json(
    method: str,
    url: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> object:
    req = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        req.add_header(key, value)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return parse_json_bytes(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print_err(f"HTTP {exc.code} from {url}")
        print_err(body)
        raise SystemExit(1) from exc
    except urllib.error.URLError as exc:
        print_err(f"Request failed: {url}")
        print_err(str(exc.reason))
        raise SystemExit(1) from exc


def build_multipart_form(file_path: Path, field_name: str = "file") -> tuple[bytes, str]:
    boundary = f"----MoDoraBoundary{uuid.uuid4().hex}"
    file_name = file_path.name
    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()

    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{file_name}"\r\n'
        ).encode("utf-8"),
        f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
        file_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    return b"".join(parts), boundary


def build_upload_form(file_path: Path, settings: dict) -> tuple[bytes, str]:
    boundary = f"----MoDoraBoundary{uuid.uuid4().hex}"
    file_name = file_path.name
    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()
    settings_json = json.dumps(settings, ensure_ascii=False)

    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        ).encode("utf-8"),
        f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
        file_bytes,
        b"\r\n",
        f"--{boundary}\r\n".encode("utf-8"),
        b'Content-Disposition: form-data; name="settings"\r\n\r\n',
        settings_json.encode("utf-8"),
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    return b"".join(parts), boundary


def upload_file(file_path: Path, settings: dict) -> object:
    body, boundary = build_upload_form(file_path, settings)
    return request_json(
        "POST",
        f"{get_base_url()}/api/upload",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            **SKILL_HEADERS,
        },
        timeout=300,
    )


def get_status(filename: str) -> object:
    quoted = urllib.parse.quote(filename)
    return request_json(
        "GET",
        f"{get_base_url()}/api/task/status/{quoted}",
        headers=SKILL_HEADERS,
    )


def chat(filename: str, question: str, settings: dict) -> object:
    payload = json.dumps(
        {"file_name": filename, "query": question, "settings": settings},
        ensure_ascii=False,
    ).encode("utf-8")
    return request_json(
        "POST",
        f"{get_base_url()}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json", **SKILL_HEADERS},
        timeout=300,
    )


def health() -> object:
    return request_json("GET", f"{get_base_url()}/health")


def wait_until_completed(
    filename: str, timeout_seconds: int = 600, poll_interval: float = 2.0
) -> object:
    deadline = time.time() + timeout_seconds
    last_payload: object | None = None

    while time.time() < deadline:
        last_payload = get_status(filename)
        status = (
            last_payload.get("status")
            if isinstance(last_payload, dict)
            else None
        )
        print(json.dumps(last_payload, ensure_ascii=False))

        if status == "completed":
            return last_payload
        if status == "failed":
            raise SystemExit("Document processing failed.")

        time.sleep(poll_interval)

    raise SystemExit(f"Timed out waiting for document processing: {filename}")
