"""Authenticated session, MFA and password management."""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Response
from sqlalchemy import delete

from app.commerce.account import mfa, schemas
from app.commerce.account.hooks import password_policy
from app.commerce.account.models import RecoveryCode, UserSession
from app.commerce.account.repository import security_for
from app.commerce.account.sessions import logout, revoke_all
from app.commerce.core.audit import audit
from app.commerce.core.deps import MallContext
from app.commerce.core.errors import MallError
from app.commerce.core.repository import owned, owned_page
from app.commerce.core.schemas import view
from app.core.config import get_settings
from app.services.auth.password import hash_password, verify_password

router = APIRouter()
SESSION_FIELDS = ("id", "device", "user_agent", "last_active", "created_at", "expires_at", "revoked_at")


@router.get("/sessions")
async def sessions(ctx: MallContext, cursor: str = ""):
    rows, after = await owned_page(ctx.db, UserSession, owner_id=ctx.user.id, cursor=cursor)
    return {"items": [view(row, SESSION_FIELDS) for row in rows], "next_cursor": after}


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, ctx: MallContext):
    row = await owned(ctx.db, UserSession, owner_id=ctx.user.id, resource_id=session_id)
    row.revoked_at = datetime.now(UTC)
    await audit(ctx.db, actor_id=ctx.user.id, action="session_revoke", resource_id=session_id)
    return {"status": "revoked"}


@router.post("/sessions/revoke-all")
async def revoke_sessions(ctx: MallContext):
    await revoke_all(ctx.db, ctx.user.id)
    await audit(ctx.db, actor_id=ctx.user.id, action="sessions_revoke_all")
    return {"status": "revoked"}


@router.post("/logout")
async def logout_api(ctx: MallContext, response: Response):
    await logout(ctx.db, ctx.claims)
    response.delete_cookie("mall_refresh", path="/api/v1/mall/account")
    response.delete_cookie("mall_csrf", path="/")
    return {"status": "logged_out"}


@router.post("/step-up")
async def step_up(payload: schemas.StepUp, ctx: MallContext):
    return await mfa.issue_step_up(ctx, payload)


@router.post("/mfa/setup")
async def mfa_setup(ctx: MallContext):
    _recent_login(ctx)
    return await mfa.setup(ctx.db, ctx.user)


@router.post("/mfa/enable")
async def mfa_enable(payload: schemas.MfaCode, ctx: MallContext):
    _recent_login(ctx)
    return await mfa.enable(ctx.db, ctx.user, payload)


@router.post("/mfa/disable")
async def mfa_disable(payload: schemas.MfaCode, ctx: MallContext):
    _recent_login(ctx)
    await mfa.verify_factor(ctx.db, ctx.user.id, payload)
    security = await security_for(ctx.db, ctx.user.id)
    security.mfa_enabled, security.totp_cipher, security.pending_totp_cipher = False, "", ""
    await ctx.db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == ctx.user.id))
    await revoke_all(ctx.db, ctx.user.id)
    await audit(ctx.db, actor_id=ctx.user.id, action="mfa_disable")
    return {"status": "disabled"}


@router.post("/password/change")
async def change_password(payload: schemas.ChangePassword, ctx: MallContext):
    mfa.require_step_up(ctx, payload.step_up_token, purpose="password_change")
    valid = await asyncio.to_thread(verify_password, payload.old_password, ctx.user.hashed_password)
    if not valid:
        raise MallError("invalid_credentials", status=401)
    await password_policy(payload.new_password)
    ctx.user.hashed_password = await asyncio.to_thread(hash_password, payload.new_password)
    await revoke_all(ctx.db, ctx.user.id)
    await audit(ctx.db, actor_id=ctx.user.id, action="password_change")
    return {"status": "changed"}


def _recent_login(ctx):
    elapsed = datetime.now(UTC).timestamp() - ctx.claims.get("iat", 0)
    if elapsed > get_settings().mall_step_up_seconds:
        raise MallError("recent_login_required", status=403)
