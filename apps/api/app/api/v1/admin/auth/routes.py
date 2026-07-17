"""Auth routes: register / login / me (PRD §4.1 / §7.1)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth.service import AuthError, AuthService

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> UserOut:
    from app.core.config import get_settings

    if get_settings().disable_local_register:
        raise HTTPException(status_code=403, detail="Local registration disabled; use SSO")
    try:
        return await AuthService(db).register(payload)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    try:
        return await AuthService(db).login(payload)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser, db: DbSession) -> UserOut:
    return await AuthService(db).me(user)
