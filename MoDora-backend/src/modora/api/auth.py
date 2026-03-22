from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from modora.core.auth.service import (
    AuthError,
    AuthUser,
    authenticate_user,
    create_session,
    create_user,
    delete_session,
    get_user_by_session,
)
from modora.core.settings import Settings

router = APIRouter(tags=["auth"])


class AuthRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    status: str
    created_at: str


class AuthResponse(BaseModel):
    user: UserResponse


def _settings() -> Settings:
    return Settings.load()


def _set_session_cookie(response: Response, settings: Settings, session_id: str) -> None:
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=session_id,
        max_age=settings.auth_session_ttl_seconds,
        httponly=True,
        secure=True,
        samesite="none",
        domain=settings.auth_cookie_domain,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_session_cookie_name,
        domain=settings.auth_cookie_domain,
        path="/",
        secure=True,
        httponly=True,
        samesite="none",
    )


def _serialize_user(user: AuthUser) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        status=user.status,
        created_at=user.created_at,
    )


def get_optional_current_user(
    request: Request,
    settings: Settings = Depends(_settings),
) -> AuthUser | None:
    session_id = request.cookies.get(settings.auth_session_cookie_name, "")
    return get_user_by_session(settings, session_id)


def require_current_user(
    user: AuthUser | None = Depends(get_optional_current_user),
) -> AuthUser:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )
    return user


@router.post("/auth/register", response_model=AuthResponse, status_code=201)
def register(
    payload: AuthRequest,
    response: Response,
    settings: Settings = Depends(_settings),
):
    try:
        user = create_user(settings, payload.email, payload.password)
        session_id, _ = create_session(settings, user.id)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _set_session_cookie(response, settings, session_id)
    return AuthResponse(user=_serialize_user(user))


@router.post("/auth/login", response_model=AuthResponse)
def login(
    payload: AuthRequest,
    response: Response,
    settings: Settings = Depends(_settings),
):
    try:
        user = authenticate_user(settings, payload.email, payload.password)
        session_id, _ = create_session(settings, user.id)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _set_session_cookie(response, settings, session_id)
    return AuthResponse(user=_serialize_user(user))


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    settings: Settings = Depends(_settings),
):
    session_id = request.cookies.get(settings.auth_session_cookie_name, "")
    delete_session(settings, session_id)
    _clear_session_cookie(response, settings)
    return Response(status_code=204)


@router.get("/auth/me", response_model=AuthResponse)
def me(user: AuthUser = Depends(require_current_user)):
    return AuthResponse(user=_serialize_user(user))
