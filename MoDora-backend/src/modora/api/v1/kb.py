from __future__ import annotations

import logging
from fastapi import APIRouter

from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths
from modora.core.services.kb import KnowledgeBaseManager
from modora.api.v1.models import UpdateTagsRequest

router = APIRouter(tags=["kb"])
logger = logging.getLogger("modora.api")

@router.get("/kb/docs")
def get_kb_docs():
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    return kb.get_all_docs()

@router.get("/kb/tags")
def get_kb_tags():
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    return kb.get_tag_library()

@router.post("/kb/doc/tags")
def update_kb_doc_tags(request: UpdateTagsRequest):
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    kb.update_doc_tags(request.file_name, request.tags)
    return {"status": "success"}

@router.delete("/kb/tag/{tag}")
def delete_kb_tag(tag: str):
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")
    kb.delete_tag_from_library(tag)
    return {"status": "success"}

@router.delete("/kb/delete/{file_name}")
def delete_kb_doc(file_name: str):
    settings = Settings.load()
    paths = resolve_paths(settings)
    kb = KnowledgeBaseManager(paths.cache_dir / "knowledge_base.json")

    source_path = paths.docs_dir / file_name
    if source_path.exists():
        source_path.unlink()

    cache_path = paths.doc_cache_dir(file_name)
    if cache_path.exists():
        import shutil
        shutil.rmtree(cache_path)

    kb.delete_doc(file_name)
    return {"status": "success", "message": f"File {file_name} deleted successfully"}
