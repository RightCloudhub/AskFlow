"""Opaque refresh rotation, replay-family revocation and strict access validation."""

import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.commerce.account.crypto import digest
from app.commerce.account.models import AccessRevocation, UserSecurity, UserSession
from app.commerce.account.repository import identity_by_id, security_for
from app.commerce.core.audit import audit
from app.commerce.core.constants import ASSURANCE_AUTHENTICATED, NAME_SIZE, SECONDS_PER_MINUTE, TOKEN_BYTES
from app.commerce.core.errors import MallError
from app.commerce.core.repository import insert_once, owned
from app.commerce.core.schemas import utc
from app.core.config import get_settings
from app.core.security import create_access_token
from app.models.mixins import new_uuid
from app.plugins.runtime import get_app_context


async def issue_session(db, user, *, device: str = "", ip: str = "", user_agent: str = "",
                        family_id: str | None = None, parent_id: str | None = None, method: str = "password"):
    settings, now = get_settings(), datetime.now(UTC)
    raw, csrf, sid = secrets.token_urlsafe(TOKEN_BYTES), secrets.token_urlsafe(TOKEN_BYTES), new_uuid()
    security = await security_for(db, user.id)
    row = UserSession(id=sid, user_id=user.id, family_id=family_id or new_uuid(), parent_id=parent_id,
        refresh_hash=digest("refresh:" + raw), csrf_hash=digest("csrf:" + csrf), device=device[:NAME_SIZE],
        ip_hash=digest("ip:" + ip), user_agent=user_agent[:NAME_SIZE], last_active=now,
        expires_at=now + timedelta(days=settings.mall_refresh_days), auth_method=method)
    db.add(row)
    await db.flush()
    access = create_access_token(user.id, role=user.role, expires_minutes=settings.mall_access_minutes,
        extra={"sid": sid, "family_id": row.family_id, "type": "access", "assurance": ASSURANCE_AUTHENTICATED,
               "auth_epoch": security.auth_epoch, "auth_method": method})
    return {"access_token": access, "refresh_token": raw, "csrf_token": csrf,
            "token_type": "bearer", "expires_in": settings.mall_access_minutes * SECONDS_PER_MINUTE}


async def rotate(db, raw: str, *, csrf: str | None = None):
    row = await db.scalar(select(UserSession).where(UserSession.refresh_hash == digest("refresh:" + raw)))
    if row is None:
        raise MallError("invalid_credentials", status=401)
    if csrf is not None and not hmac.compare_digest(row.csrf_hash, digest("csrf:" + csrf)):
        raise MallError("csrf_invalid", status=403)
    user = await identity_by_id(db, row.user_id, lock=True)
    if user is None:
        raise MallError("invalid_credentials", status=401)
    now = datetime.now(UTC)
    changed = await db.execute(update(UserSession).where(UserSession.id == row.id,
        UserSession.consumed_at.is_(None), UserSession.revoked_at.is_(None), UserSession.expires_at > now)
        .values(consumed_at=now).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        await db.execute(update(UserSession).where(UserSession.family_id == row.family_id).values(revoked_at=now))
        await audit(db, actor_id=row.user_id, action="refresh_replay", resource_id=row.family_id)
        raise MallError("invalid_credentials", status=401, persist=True)
    return await issue_session(db, user, device=row.device, family_id=row.family_id,
                               parent_id=row.id, method=row.auth_method)


async def validate_access(db, claims: dict):
    ctx = get_app_context()
    if ctx is None or not ctx.enabled("mall_account"):
        return
    if claims.get("type", "access") != "access":
        raise MallError("invalid_credentials", status=401)
    from app.commerce.account.session_store import store

    revoked = await store().revoked(db, claims)
    security = await db.scalar(select(UserSecurity).where(UserSecurity.user_id == claims.get("sub")))
    if revoked or (security and claims.get("auth_epoch", 0) != security.auth_epoch):
        raise MallError("invalid_credentials", status=401)
    sid = claims.get("sid")
    if not sid:
        if security and security.mfa_enabled:
            raise MallError("invalid_credentials", status=401)
        return
    row = await db.scalar(select(UserSession).where(UserSession.id == sid, UserSession.user_id == claims.get("sub")))
    if row is None or row.revoked_at or utc(row.expires_at) <= datetime.now(UTC):
        raise MallError("invalid_credentials", status=401)


async def revoke_all(db, user_id: str):
    await db.execute(update(UserSession).where(UserSession.user_id == user_id)
                     .values(revoked_at=datetime.now(UTC)))
    security = await security_for(db, user_id)
    security.auth_epoch += 1
    await db.flush()


async def revoke_family(db, row):
    await db.execute(update(UserSession).where(UserSession.user_id == row.user_id,
        UserSession.family_id == row.family_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC)))


async def logout(db, claims: dict):
    if claims.get("jti"):
        await insert_once(db, AccessRevocation, values={"jti": claims["jti"], "user_id": claims["sub"],
            "expires_at": datetime.fromtimestamp(claims["exp"], UTC)}, unique=["jti"])
    if claims.get("sid"):
        row = await owned(db, UserSession, owner_id=claims["sub"], resource_id=claims["sid"])
        await revoke_family(db, row)
    await audit(db, actor_id=claims["sub"], action="logout")


async def legacy_token_extra(db, user_id: str) -> dict:
    ctx = get_app_context()
    if ctx is None or not ctx.enabled("mall_account"):
        return {}
    security = await db.scalar(select(UserSecurity).where(UserSecurity.user_id == user_id))
    if security is not None and security.mfa_enabled:
        raise ValueError("invalid_credentials")
    return {"auth_epoch": security.auth_epoch if security else 0}
