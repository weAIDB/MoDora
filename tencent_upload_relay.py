#!/usr/bin/env python3

from __future__ import annotations

import base64
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile


app = FastAPI(title="MoDora Tencent Upload Relay")

SSH_HOST = os.environ.get("MODORA_SSH_HOST", "")
SSH_USER = os.environ.get("MODORA_SSH_USER", "yukai")
REMOTE_PROJECT_ROOT = os.environ.get("MODORA_PROJECT_ROOT", "/home/yukai/project/MoDora")
REMOTE_DOCS_DIR = os.environ.get("MODORA_DOCS_DIR", f"{REMOTE_PROJECT_ROOT}/datasets/MMDA")
UPLOAD_TMP_DIR = Path(os.environ.get("UPLOAD_TMP_DIR", "/tmp/modora_uploads"))
CHUNK_SIZE = 1024 * 1024


def require_env(name: str, value: str) -> None:
    if not value:
        raise HTTPException(status_code=500, detail=f"Missing required env: {name}")


def safe_filename(name: str) -> str:
    return Path(name).name


def run_checked(cmd: list[str], detail: str) -> None:
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or detail
        raise HTTPException(status_code=502, detail=f"{detail}: {message}") from exc


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    settings: str | None = Form(None),
):
    require_env("MODORA_SSH_HOST", SSH_HOST)
    filename = safe_filename(file.filename or "")
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    UPLOAD_TMP_DIR.mkdir(parents=True, exist_ok=True)
    local_path = UPLOAD_TMP_DIR / filename

    try:
        with local_path.open("wb") as buffer:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                buffer.write(chunk)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to receive upload: {exc}") from exc
    finally:
        await file.close()

    remote_target = f"{SSH_USER}@{SSH_HOST}:{REMOTE_DOCS_DIR}/{filename}"
    run_checked(
        ["scp", str(local_path), remote_target],
        "Failed to copy file to MoDora server",
    )

    settings_b64 = ""
    if settings:
        try:
            settings_b64 = base64.b64encode(
                json.dumps(json.loads(settings), ensure_ascii=False).encode("utf-8")
            ).decode("ascii")
        except Exception:
            settings_b64 = ""

    remote_log = f"/tmp/modora-process-{filename.replace('/', '_')}.log"
    remote_cmd = (
        f"cd {shlex.quote(REMOTE_PROJECT_ROOT)} && "
        f"nohup ./process_local_pdf.sh {shlex.quote(filename)} {shlex.quote(settings_b64)} "
        f">{shlex.quote(remote_log)} 2>&1 </dev/null &"
    )
    run_checked(
        ["ssh", f"{SSH_USER}@{SSH_HOST}", remote_cmd],
        "Failed to start remote document processing",
    )

    return {
        "filename": filename,
        "status": "uploaded",
        "message": "File uploaded to relay and queued for remote processing.",
    }
