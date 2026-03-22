from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import sqlite3

from modora.core.auth.security import (
    generate_session_id,
    generate_user_id,
    hash_password,
    verify_password,
)
from modora.core.persistence import connect_db
from modora.core.settings import Settings


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    status: str
    created_at: str


class AuthError(ValueError):
    pass


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized:
        raise AuthError("email is required")
    return normalized


def _serialize_user(row: sqlite3.Row | None) -> AuthUser | None:
    if row is None:
        return None
    return AuthUser(
        id=row["id"],
        email=row["email"],
        status=row["status"],
        created_at=row["created_at"],
    )


def create_user(settings: Settings, email: str, password: str) -> AuthUser:
    email = _normalize_email(email)
    password = password.strip()
    if len(password) < 8:
        raise AuthError("password must be at least 8 characters")

    created_at = datetime.now(timezone.utc).isoformat()
    user_id = generate_user_id()
    password_hash = hash_password(password)

    try:
        with connect_db(settings) as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, status, created_at)
                VALUES (?, ?, ?, 'active', ?)
                """,
                (user_id, email, password_hash, created_at),
            )
            row = conn.execute(
                "SELECT id, email, status, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
    except sqlite3.IntegrityError as exc:
        raise AuthError("email already registered") from exc

    user = _serialize_user(row)
    if user is None:
        raise AuthError("failed to create user")
    return user


def authenticate_user(settings: Settings, email: str, password: str) -> AuthUser:
    email = _normalize_email(email)

    with connect_db(settings) as conn:
        row = conn.execute(
            """
            SELECT id, email, password_hash, status, created_at
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if row is None or not verify_password(password, row["password_hash"]):
        raise AuthError("invalid email or password")

    if row["status"] != "active":
        raise AuthError("user is not active")

    user = _serialize_user(row)
    if user is None:
        raise AuthError("failed to load user")
    return user


def create_session(settings: Settings, user_id: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.auth_session_ttl_seconds)
    session_id = generate_session_id()

    with connect_db(settings) as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, user_id, expires_at.isoformat(), now.isoformat()),
        )

    return session_id, expires_at.isoformat()


def delete_session(settings: Settings, session_id: str) -> None:
    if not session_id:
        return
    with connect_db(settings) as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def get_user_by_session(settings: Settings, session_id: str) -> AuthUser | None:
    if not session_id:
        return None

    now = datetime.now(timezone.utc).isoformat()
    with connect_db(settings) as conn:
        row = conn.execute(
            """
            SELECT u.id, u.email, u.status, u.created_at, s.expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.id = ?
            """,
            (session_id,),
        ).fetchone()

        if row is None:
            return None

        if row["expires_at"] <= now:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return None

    return AuthUser(
        id=row["id"],
        email=row["email"],
        status=row["status"],
        created_at=row["created_at"],
    )
