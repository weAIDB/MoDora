from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import secrets
import sqlite3
from typing import Iterable

from modora.core.persistence import connect_db
from modora.core.settings import Settings


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    user_id: str
    original_name: str
    storage_key: str
    status: str
    created_at: str


@dataclass(frozen=True)
class JobRecord:
    id: str
    user_id: str
    document_id: str | None
    type: str
    status: str
    error: str | None
    created_at: str


def _doc_from_row(row: sqlite3.Row | None) -> DocumentRecord | None:
    if row is None:
        return None
    return DocumentRecord(
        id=row["id"],
        user_id=row["user_id"],
        original_name=row["original_name"],
        storage_key=row["storage_key"],
        status=row["status"],
        created_at=row["created_at"],
    )


def _job_from_row(row: sqlite3.Row | None) -> JobRecord | None:
    if row is None:
        return None
    return JobRecord(
        id=row["id"],
        user_id=row["user_id"],
        document_id=row["document_id"],
        type=row["type"],
        status=row["status"],
        error=row["error"],
        created_at=row["created_at"],
    )


def generate_document_id() -> str:
    return f"doc_{secrets.token_urlsafe(12)}"


def generate_job_id() -> str:
    return f"job_{secrets.token_urlsafe(12)}"


def create_document(
    settings: Settings,
    *,
    user_id: str,
    original_name: str,
    storage_key: str,
    status: str = "uploaded",
) -> DocumentRecord:
    document_id = generate_document_id()
    created_at = datetime.now(timezone.utc).isoformat()
    with connect_db(settings) as conn:
        conn.execute(
            """
            INSERT INTO documents (id, user_id, original_name, storage_key, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (document_id, user_id, original_name, storage_key, status, created_at),
        )
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    doc = _doc_from_row(row)
    if doc is None:
        raise ValueError("failed to create document")
    return doc


def create_job(
    settings: Settings,
    *,
    user_id: str,
    document_id: str | None,
    job_type: str,
    status: str = "pending",
    error: str | None = None,
) -> JobRecord:
    job_id = generate_job_id()
    created_at = datetime.now(timezone.utc).isoformat()
    with connect_db(settings) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, user_id, document_id, type, status, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, user_id, document_id, job_type, status, error, created_at),
        )
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    job = _job_from_row(row)
    if job is None:
        raise ValueError("failed to create job")
    return job


def update_document_status(
    settings: Settings,
    document_id: str,
    *,
    status: str,
) -> None:
    with connect_db(settings) as conn:
        conn.execute(
            "UPDATE documents SET status = ? WHERE id = ?",
            (status, document_id),
        )


def update_document_storage_key(
    settings: Settings,
    document_id: str,
    *,
    storage_key: str,
) -> None:
    with connect_db(settings) as conn:
        conn.execute(
            "UPDATE documents SET storage_key = ? WHERE id = ?",
            (storage_key, document_id),
        )


def update_job_status(
    settings: Settings,
    job_id: str,
    *,
    status: str,
    error: str | None = None,
) -> None:
    with connect_db(settings) as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, error = ? WHERE id = ?",
            (status, error, job_id),
        )


def get_document_by_id(
    settings: Settings,
    *,
    user_id: str,
    document_id: str,
) -> DocumentRecord | None:
    with connect_db(settings) as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ? AND user_id = ?",
            (document_id, user_id),
        ).fetchone()
    return _doc_from_row(row)


def get_document_by_name(
    settings: Settings,
    *,
    user_id: str,
    name: str,
) -> DocumentRecord | None:
    with connect_db(settings) as conn:
        row = conn.execute(
            """
            SELECT * FROM documents
            WHERE user_id = ?
              AND (id = ? OR original_name = ? OR storage_key = ?)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, name, name, name),
        ).fetchone()
    return _doc_from_row(row)


def get_job_by_id(
    settings: Settings,
    *,
    user_id: str,
    job_id: str,
) -> JobRecord | None:
    with connect_db(settings) as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
    return _job_from_row(row)


def list_documents_for_user(settings: Settings, *, user_id: str) -> list[DocumentRecord]:
    with connect_db(settings) as conn:
        rows: Iterable[sqlite3.Row] = conn.execute(
            """
            SELECT * FROM documents
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [_doc_from_row(row) for row in rows if _doc_from_row(row) is not None]


def delete_document(
    settings: Settings,
    *,
    user_id: str,
    document_id: str,
) -> None:
    with connect_db(settings) as conn:
        conn.execute(
            "DELETE FROM documents WHERE id = ? AND user_id = ?",
            (document_id, user_id),
        )
