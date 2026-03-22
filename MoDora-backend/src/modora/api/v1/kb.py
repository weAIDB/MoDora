from __future__ import annotations

import logging
import shutil

from fastapi import APIRouter, Depends, HTTPException

from modora.api.auth import get_optional_current_user
from modora.api.v1.document_access import resolve_document_paths
from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths
from modora.core.services.kb import KnowledgeBaseManager
from modora.core.services.retrieve import delete_source_index
from modora.core.auth.service import AuthUser
from modora.core.persistence.documents import delete_document
from modora.api.v1.models import UpdateTagsRequest

router = APIRouter(tags=["kb"])
logger = logging.getLogger("modora.api")


@router.get("/kb/docs")
def get_kb_docs(user: AuthUser | None = Depends(get_optional_current_user)):
    settings = Settings.load()
    paths = resolve_paths(settings)
    target_paths = paths.user_paths(user.id) if user is not None else paths
    kb = KnowledgeBaseManager(getattr(target_paths, "kb_path", target_paths.cache_dir / "knowledge_base.json"))
    return kb.get_all_docs()


@router.get("/kb/tags")
def get_kb_tags(user: AuthUser | None = Depends(get_optional_current_user)):
    settings = Settings.load()
    paths = resolve_paths(settings)
    target_paths = paths.user_paths(user.id) if user is not None else paths
    kb = KnowledgeBaseManager(getattr(target_paths, "kb_path", target_paths.cache_dir / "knowledge_base.json"))
    return kb.get_tag_library()


@router.post("/kb/doc/tags")
def update_kb_doc_tags(
    request: UpdateTagsRequest,
    user: AuthUser | None = Depends(get_optional_current_user),
):
    settings = Settings.load()
    resolved = resolve_document_paths(
        settings,
        user=user,
        document_id=request.document_id,
        file_name=request.file_name,
    )
    kb = KnowledgeBaseManager(resolved.kb_path)
    kb.update_doc_tags(resolved.storage_name, request.tags)
    return {"status": "success"}


@router.delete("/kb/tag/{tag}")
def delete_kb_tag(
    tag: str,
    user: AuthUser | None = Depends(get_optional_current_user),
):
    settings = Settings.load()
    paths = resolve_paths(settings)
    target_paths = paths.user_paths(user.id) if user is not None else paths
    kb = KnowledgeBaseManager(getattr(target_paths, "kb_path", target_paths.cache_dir / "knowledge_base.json"))
    kb.delete_tag_from_library(tag)
    return {"status": "success"}


@router.delete("/kb/delete/{file_name}")
def delete_kb_doc(
    file_name: str,
    user: AuthUser | None = Depends(get_optional_current_user),
):
    settings = Settings.load()
    resolved = resolve_document_paths(settings, user=user, file_name=file_name)
    kb = KnowledgeBaseManager(resolved.kb_path)
    delete_source_index(settings, source_path=str(resolved.source_path))

    source_path = resolved.source_path
    if source_path.exists():
        source_path.unlink()

    cache_path = resolved.cache_dir
    if cache_path.exists():
        shutil.rmtree(cache_path)

    kb.delete_doc(resolved.storage_name)
    if user is not None and resolved.document_id is not None:
        delete_document(settings, user_id=user.id, document_id=resolved.document_id)
    return {"status": "success", "message": f"File {resolved.display_name} deleted successfully"}


@router.delete("/kb/doc/{document_id}")
def delete_kb_doc_by_document_id(
    document_id: str,
    user: AuthUser = Depends(get_optional_current_user),
):
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    settings = Settings.load()
    resolved = resolve_document_paths(settings, user=user, document_id=document_id)
    kb = KnowledgeBaseManager(resolved.kb_path)
    delete_source_index(settings, source_path=str(resolved.source_path))

    if resolved.source_path.exists():
        resolved.source_path.unlink()
    if resolved.cache_dir.exists():
        shutil.rmtree(resolved.cache_dir)
    kb.delete_doc(resolved.storage_name)
    if resolved.document_id is not None:
        delete_document(settings, user_id=user.id, document_id=resolved.document_id)
    return {"status": "success", "message": f"File {resolved.display_name} deleted successfully"}
