from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import fitz
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from modora.api.auth import get_optional_current_user
from modora.api.v1.models import DocumentItem, DocumentListResponse, TaskStatusResponse, UploadResponse
from modora.core.auth.service import AuthUser
from modora.core.persistence.documents import (
    create_document,
    create_job,
    get_document_by_id,
    get_job_by_id,
    list_documents_for_user,
    update_document_status,
    update_document_storage_key,
)
from modora.core.persistence.user_preferences import effective_settings_for_user
from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths
from modora.core.utils.config import settings_from_ui_payload
from modora.core.services.task_store import TASK_STATUS
from modora.core.services.document_processing import process_document_task

router = APIRouter(tags=["documents"])
logger = logging.getLogger("modora.api")


def _settings_from_payload(
    payload: dict[str, Any] | None,
    *,
    user: AuthUser | None,
) -> Settings:
    settings = effective_settings_for_user(Settings.load(), user_id=user.id if user else None)
    settings, _, _, _ = settings_from_ui_payload(
        settings, payload, module_key="levelGenerator"
    )
    return settings


@router.get("/pdf/{file_name}/{page_index}/image")
def get_pdf_image(
    file_name: str,
    page_index: int,
    user: AuthUser | None = Depends(get_optional_current_user),
):
    settings = Settings.load()
    paths = resolve_paths(settings)
    if user is not None:
        source_path = paths.user_paths(user.id).docs_dir / Path(file_name).name
    else:
        source_path = paths.docs_dir / Path(file_name).name
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


@router.get("/task/status/{filename}", response_model=TaskStatusResponse)
def get_task_status(
    filename: str,
    user: AuthUser | None = Depends(get_optional_current_user),
):
    settings = Settings.load()
    paths = resolve_paths(settings)
    if user is not None:
        job = get_job_by_id(settings, user_id=user.id, job_id=filename)
        if job is not None:
            status = TASK_STATUS.get_for_user(user.id, filename)
            if status == "unknown":
                status = job.status
            return TaskStatusResponse(
                status=status,
                document_id=job.document_id,
                job_id=job.id,
            )

        doc = get_document_by_id(settings, user_id=user.id, document_id=filename)
        if doc is not None:
            status = doc.status
            return TaskStatusResponse(status=status, document_id=doc.id)

        status = TASK_STATUS.get_for_user(user.id, filename)
        if status == "unknown":
            doc_cache = paths.user_paths(user.id).doc_cache_dir(filename)
            if (doc_cache / "tree.json").exists():
                status = "completed"
        return TaskStatusResponse(status=status)

    status = TASK_STATUS.get(filename)
    if status == "unknown":
        doc_cache = paths.doc_cache_dir(filename)
        if (doc_cache / "tree.json").exists():
            status = "completed"
    return TaskStatusResponse(status=status)


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(user: AuthUser = Depends(get_optional_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")

    settings = Settings.load()
    documents = list_documents_for_user(settings, user_id=user.id)
    return DocumentListResponse(
        documents=[
            DocumentItem(
                id=doc.id,
                original_name=doc.original_name,
                storage_key=doc.storage_key,
                status=doc.status,
                created_at=doc.created_at,
            )
            for doc in documents
        ]
    )


@router.get("/documents/{document_id}/pdf/{page_index}/image")
def get_pdf_image_by_document_id(
    document_id: str,
    page_index: int,
    user: AuthUser = Depends(get_optional_current_user),
):
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")

    settings = Settings.load()
    document = get_document_by_id(settings, user_id=user.id, document_id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    source_path = resolve_paths(settings).user_paths(user.id).docs_dir / document.storage_key
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


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: str,
    user: AuthUser = Depends(get_optional_current_user),
):
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")

    settings = Settings.load()
    document = get_document_by_id(settings, user_id=user.id, document_id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    source_path = resolve_paths(settings).user_paths(user.id).docs_dir / document.storage_key
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(source_path),
        media_type="application/pdf",
        filename=document.original_name,
    )


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: str | None = Form(None),
    user: AuthUser | None = Depends(get_optional_current_user),
):
    cfg: dict[str, Any] | None = None
    if settings:
        try:
            cfg = json.loads(settings)
        except json.JSONDecodeError:
            cfg = {}

    app_settings = _settings_from_payload(cfg, user=user)
    paths = resolve_paths(app_settings)
    original_name = Path(file.filename or "").name
    if not original_name:
        raise HTTPException(status_code=400, detail="filename is required")

    document_id: str | None = None
    job_id: str | None = None
    status_key = original_name
    status_user_id: str | None = None

    if user is not None:
        user_paths = paths.user_paths(user.id)
        document = create_document(
            app_settings,
            user_id=user.id,
            original_name=original_name,
            storage_key="pending",
        )
        document_id = document.id
        storage_name = f"{document_id}_{original_name}"
        file_location = user_paths.docs_dir / storage_name
        update_document_status(app_settings, document_id, status="pending")
        update_document_storage_key(
            app_settings,
            document_id,
            storage_key=storage_name,
        )
        job = create_job(
            app_settings,
            user_id=user.id,
            document_id=document_id,
            job_type="document_process",
            status="pending",
        )
        job_id = job.id
        status_key = job_id
        status_user_id = user.id
        target_paths = user_paths
    else:
        file_location = paths.docs_dir / original_name
        target_paths = paths

    try:
        with file_location.open("wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)
        logger.info(f"Saved uploaded file: {file_location}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {e}")
    finally:
        await file.close()

    if status_user_id:
        TASK_STATUS.set_for_user(status_user_id, status_key, "pending")
    else:
        TASK_STATUS.set(status_key, "pending")
    background_tasks.add_task(
        process_document_task,
        str(file_location),
        target_paths,
        app_settings,
        cfg,
        logger,
        status_key=status_key,
        status_user_id=status_user_id,
        document_id=document_id,
        job_id=job_id,
    )
    return UploadResponse(
        filename=original_name,
        status="uploaded",
        message="File uploaded. Processing in background.",
        document_id=document_id,
        job_id=job_id,
    )
