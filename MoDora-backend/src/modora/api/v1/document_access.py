from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

from modora.core.auth.service import AuthUser
from modora.core.persistence.documents import DocumentRecord, get_document_by_id, get_document_by_name
from modora.core.settings import Settings
from modora.core.utils.paths import AppPaths, UserPaths, resolve_paths


@dataclass(frozen=True)
class ResolvedDocument:
    document_id: str | None
    display_name: str
    storage_name: str
    source_path: Path
    cache_dir: Path
    kb_path: Path
    user_id: str | None = None


def _kb_path(paths: AppPaths | UserPaths) -> Path:
    return getattr(paths, "kb_path", paths.cache_dir / "knowledge_base.json")


def resolve_document_paths(
    settings: Settings,
    *,
    user: AuthUser | None,
    document_id: str | None = None,
    file_name: str | None = None,
) -> ResolvedDocument:
    paths = resolve_paths(settings)

    if user is not None:
        user_paths = paths.user_paths(user.id)
        document: DocumentRecord | None = None
        if document_id:
            document = get_document_by_id(settings, user_id=user.id, document_id=document_id)
        elif file_name:
            document = get_document_by_name(settings, user_id=user.id, name=file_name)

        if document is not None:
            return ResolvedDocument(
                document_id=document.id,
                display_name=document.original_name,
                storage_name=document.storage_key,
                source_path=user_paths.docs_dir / document.storage_key,
                cache_dir=user_paths.doc_cache_dir(document.storage_key),
                kb_path=_kb_path(user_paths),
                user_id=user.id,
            )

        if document_id:
            raise HTTPException(status_code=404, detail="Document not found")

        if file_name:
            fallback_name = Path(file_name).name
            return ResolvedDocument(
                document_id=None,
                display_name=fallback_name,
                storage_name=fallback_name,
                source_path=user_paths.docs_dir / fallback_name,
                cache_dir=user_paths.doc_cache_dir(fallback_name),
                kb_path=_kb_path(user_paths),
                user_id=user.id,
            )

    if not file_name:
        raise HTTPException(status_code=400, detail="file_name or document_id is required")

    fallback_name = Path(file_name).name
    return ResolvedDocument(
        document_id=None,
        display_name=fallback_name,
        storage_name=fallback_name,
        source_path=paths.docs_dir / fallback_name,
        cache_dir=paths.doc_cache_dir(fallback_name),
        kb_path=_kb_path(paths),
        user_id=None,
    )

