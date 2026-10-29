"""Shared enforcement for legacy REST, OIDC and long-lived websocket sessions."""

from fastapi import HTTPException

from app.commerce.core.errors import MallError
from app.plugins.runtime import get_app_context


def enabled():
    ctx = get_app_context()
    return ctx is not None and ctx.enabled("mall_account")


async def validate_legacy_access(db, claims):
    if not enabled():
        return
    from app.commerce.account.sessions import validate_access

    try:
        await validate_access(db, claims)
    except MallError as exc:
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc


async def websocket_valid(websocket, db, user):
    if not enabled():
        return True
    from app.core.security import decode_access_token

    try:
        claims = decode_access_token(websocket.state.mall_token)
        await db.refresh(user)
        if not user.is_active:
            return False
        await validate_legacy_access(db, claims)
        return True
    except (ValueError, HTTPException):
        return False
