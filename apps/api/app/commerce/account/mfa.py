"""TOTP and recovery consumption are database CAS operations."""

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from jose import JWTError, jwt
from sqlalchemy import select, update

from app.commerce.account.crypto import RECOVERY_CODE_COUNT, RECOVERY_TOKEN_BYTES, decrypt, digest, encrypt, matched_step, new_totp_secret
from app.commerce.account.models import RecoveryCode, UserSecurity
from app.commerce.account.repository import security_for
from app.commerce.account.verification import consume_proof
from app.commerce.core.audit import audit
from app.commerce.core.errors import MallError
from app.core.config import get_settings


async def verify_factor(db, user_id: str, credentials):
    security = await security_for(db, user_id)
    if not security.mfa_enabled:
        return
    if credentials.recovery_code:
        changed = await db.execute(update(RecoveryCode).where(RecoveryCode.user_id == user_id,
            RecoveryCode.code_hash == digest("recovery:" + credentials.recovery_code),
            RecoveryCode.consumed_at.is_(None)).values(consumed_at=datetime.now(UTC)))
        if changed.rowcount == 1:
            return
        raise MallError("invalid_credentials", status=401)
    step = matched_step(decrypt(security.totp_cipher), credentials.totp)
    if step is None or step <= security.last_totp_step:
        raise MallError("invalid_credentials", status=401)
    changed = await db.execute(update(UserSecurity).where(UserSecurity.id == security.id,
        UserSecurity.last_totp_step < step).values(last_totp_step=step, version=UserSecurity.version + 1))
    if changed.rowcount != 1:
        raise MallError("invalid_credentials", status=401)


async def setup(db, user):
    security = await security_for(db, user.id)
    if security.mfa_enabled:
        raise MallError("mfa_already_enabled")
    secret = new_totp_secret()
    security.pending_totp_cipher = encrypt(secret)
    await audit(db, actor_id=user.id, action="mfa_setup")
    return {"secret": secret, "provisioning_uri": "otpauth://totp/AskFlow:" + quote(user.username)
            + "?secret=" + secret + "&issuer=AskFlow"}


async def enable(db, user, credentials):
    security = await security_for(db, user.id)
    if security.mfa_enabled or not security.pending_totp_cipher:
        raise MallError("mfa_setup_required")
    step = matched_step(decrypt(security.pending_totp_cipher), credentials.totp)
    if step is None:
        raise MallError("invalid_credentials", status=401)
    security.totp_cipher, security.pending_totp_cipher = security.pending_totp_cipher, ""
    security.mfa_enabled, security.last_totp_step = True, step
    codes = [secrets.token_urlsafe(RECOVERY_TOKEN_BYTES) for _ in range(RECOVERY_CODE_COUNT)]
    db.add_all([RecoveryCode(user_id=user.id, code_hash=digest("recovery:" + code)) for code in codes])
    from app.commerce.account.sessions import revoke_all

    await revoke_all(db, user.id)
    await audit(db, actor_id=user.id, action="mfa_enable")
    return {"recovery_codes": codes}


async def issue_step_up(ctx, payload):
    security = await security_for(ctx.db, ctx.user.id)
    if security.mfa_enabled:
        await verify_factor(ctx.db, ctx.user.id, payload)
    else:
        _target, proof = await consume_proof(ctx.db, payload, purpose="step-up")
        if proof.user_id != ctx.user.id:
            raise MallError("invalid_credentials", status=401)
    settings = get_settings()
    token = jwt.encode({"sub": ctx.user.id, "sid": ctx.claims.get("sid"), "purpose": payload.purpose,
        "type": "step_up", "auth_epoch": security.auth_epoch,
        "exp": datetime.now(UTC) + timedelta(seconds=settings.mall_step_up_seconds)},
        settings.mall_refresh_secret, algorithm="HS256")
    await audit(ctx.db, actor_id=ctx.user.id, action="step_up", detail={"purpose": payload.purpose})
    return {"step_up_token": token}


def require_step_up(ctx, token: str, *, purpose: str):
    try:
        data = jwt.decode(token, get_settings().mall_refresh_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise MallError("step_up_required", status=403) from exc
    expected = (ctx.user.id, ctx.claims.get("sid"), purpose, ctx.claims.get("auth_epoch", 0))
    actual = (data.get("sub"), data.get("sid"), data.get("purpose"), data.get("auth_epoch"))
    if data.get("type") != "step_up" or expected != actual:
        raise MallError("step_up_required", status=403)
