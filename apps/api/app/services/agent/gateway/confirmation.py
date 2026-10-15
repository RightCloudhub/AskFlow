"""Signed, expiring, single-use confirmation tokens bound to the pending arguments (arch §15.3)."""

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.confirmation_nonce import ConfirmationNonce
from app.services.agent.gateway.idempotency import args_hash
from app.services.agent.gateway.settings import GatewaySettings

NONCE_BYTES = 16
TOKEN_FIELDS = 5


@dataclass(frozen=True)
class ConfirmationToken:
    token: str
    nonce: str
    args_hash: str
    expires_at: datetime


def _sign(body: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, body.encode("utf-8"), hashlib.sha256).hexdigest()


async def issue_confirmation(
    db: AsyncSession,
    *,
    scope_id: str,
    step: str,
    args: dict,
    task_id: str | None = None,
    turn_id: str | None = None,
    ttl_seconds: int | None = None,
) -> ConfirmationToken:
    ttl = ttl_seconds or GatewaySettings().confirmation_ttl_seconds
    nonce = secrets.token_urlsafe(NONCE_BYTES)
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
    digest = args_hash(args)
    body = f"{scope_id}|{step}|{digest}|{int(expires_at.timestamp())}|{nonce}"
    token = base64.urlsafe_b64encode(f"{body}|{_sign(body)}".encode("utf-8")).decode("ascii")
    db.add(
        ConfirmationNonce(
            nonce=nonce,
            task_id=task_id,
            turn_id=turn_id,
            step=step,
            args_hash=digest,
            expires_at=expires_at,
        )
    )
    await db.flush()
    return ConfirmationToken(token=token, nonce=nonce, args_hash=digest, expires_at=expires_at)


async def validate_confirmation(
    db: AsyncSession, token: str, *, scope_id: str, step: str, args: dict
) -> bool:
    return await validate_confirmation_for_hash(
        db, token, scope_id=scope_id, step=step, expected_args_hash=args_hash(args)
    )


async def validate_confirmation_for_hash(
    db: AsyncSession, token: str, *, scope_id: str, step: str, expected_args_hash: str
) -> bool:
    """Verify signature, expiry, binding; consume the nonce atomically (single use)."""
    parsed = _parse(token)
    if parsed is None:
        return False
    body, sig, scope_part, step_part, digest, exp, nonce = parsed
    if not hmac.compare_digest(sig, _sign(body)):
        return False
    if scope_part != scope_id or step_part != step:
        return False
    if digest != expected_args_hash:
        return False
    if int(exp) < time.time():
        return False
    consumed = await db.execute(
        update(ConfirmationNonce)
        .where(
            ConfirmationNonce.nonce == nonce,
            ConfirmationNonce.consumed_at.is_(None),
            ConfirmationNonce.expires_at > datetime.now(UTC),
        )
        .values(consumed_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    return consumed.rowcount == 1


def _parse(token: str) -> tuple | None:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        body, sig = decoded.rsplit("|", 1)
        parts = body.split("|")
        if len(parts) != TOKEN_FIELDS:
            return None
        return (body, sig, *parts)
    except Exception:
        return None
