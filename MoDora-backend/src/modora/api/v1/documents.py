from __future__ import annotations

import json
import logging
from typing import Any

import fitz
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths
from modora.core.utils.config import settings_from_ui_payload
from modora.core.services.task_store import TASK_STATUS
from modora.core.services.document_processing import process_document_task

router = APIRouter(tags=["documents"])
logger = logging.getLogger("modora.api")


def _settings_from_payload(payload: dict[str, Any] | None) -> Settings:
    settings = Settings.load()
    settings, _, _ = settings_from_ui_payload(
        settings, payload, module_key="levelGenerator"
    )
    return settings


@router.get("/pdf/{file_name}/{page_index}/image")
def get_pdf_image(file_name: str, page_index: int):
    settings = Settings.load()
    paths = resolve_paths(settings)
    source_path = paths.docs_dir / file_name
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        doc = fitz.open(str(source_path))
        if page_index < 1 or page_index > len(doc):
            doc.close()
            raise HTTPException(status_code=400, detail="Invalid page index")

        page = doc[page_index - 1]
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        doc.close()
        return StreamingResponse(iter([img_data]), media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/status/{filename}")
def get_task_status(filename: str):
    settings = Settings.load()
    paths = resolve_paths(settings)
    status = TASK_STATUS.get(filename)
    if status == "unknown":
        doc_cache = paths.doc_cache_dir(filename)
        if (doc_cache / "tree.json").exists():
            return {"status": "completed"}
    return {"status": status}


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: str | None = Form(None),
):
    cfg: dict[str, Any] | None = None
    if settings:
        try:
            cfg = json.loads(settings)
        except json.JSONDecodeError:
            cfg = {}

    app_settings = _settings_from_payload(cfg)
    paths = resolve_paths(app_settings)

    file_location = paths.docs_dir / file.filename
    try:
        with file_location.open("wb") as buffer:
            buffer.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {e}")

    TASK_STATUS.set(file.filename, "pending")
    background_tasks.add_task(
        process_document_task,
        str(file_location),
        paths,
        app_settings,
        cfg,
        logger,
    )
    return {
        "filename": file.filename,
        "status": "uploaded",
        "message": "File uploaded. Processing in background.",
    }
