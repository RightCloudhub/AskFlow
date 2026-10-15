"""One-time step-up codes: hashed at rest, delivered through the notify webhook (arch §4.2)."""

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.core.config import get_settings
from app.models.otp_challenge import OtpChallenge
from app.services.agent.gateway.settings import GatewaySettings

OTP_DIGITS = 6
CODE_SPACE = 10**OTP_DIGITS
CODE_FORMAT = "{:06d}"
ECHO_CODE_ENVS = frozenset({"test", "development"})
OTP_EVENT = "auth.otp"
PURPOSE_STEP_UP = "step_up"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OtpIssue:
    challenge_id: str
    expires_at: datetime
    code: str | None


def _hash_code(code: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, code.encode("utf-8"), hashlib.sha256).hexdigest()


async def issue_otp(
    db, *, user_id: str, conversation_id: str, channel: str, purpose: str = PURPOSE_STEP_UP
) -> OtpIssue:
    settings = GatewaySettings()
    code = CODE_FORMAT.format(secrets.randbelow(CODE_SPACE))
    challenge = OtpChallenge(
        user_id=user_id,
        conversation_id=conversation_id,
        channel=channel,
        purpose=purpose,
        code_hash=_hash_code(code),
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.otp_ttl_seconds),
    )
    db.add(challenge)
    await db.flush()
    await _deliver(db, challenge, code)
    echo = code if get_settings().env in ECHO_CODE_ENVS else None
    return OtpIssue(challenge_id=challenge.id, expires_at=challenge.expires_at, code=echo)


async def verify_otp(db, *, conversation_id: str, code: str) -> bool:
    challenge = await _active_challenge(db, conversation_id)
    if challenge is None:
        return False
    settings = GatewaySettings()
    if challenge.attempts >= settings.otp_max_attempts:
        return False
    if not hmac.compare_digest(challenge.code_hash, _hash_code(code.strip())):
        challenge.attempts += 1
        await db.flush()
        return False
    consumed = await db.execute(
        update(OtpChallenge)
        .where(OtpChallenge.id == challenge.id, OtpChallenge.consumed_at.is_(None))
        .values(consumed_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    return consumed.rowcount == 1


async def otp_active(db, *, conversation_id: str) -> bool:
    return await _active_challenge(db, conversation_id) is not None


async def _active_challenge(db, conversation_id: str) -> OtpChallenge | None:
    return await db.scalar(
        select(OtpChallenge)
        .where(
            OtpChallenge.conversation_id == conversation_id,
            OtpChallenge.consumed_at.is_(None),
            OtpChallenge.expires_at > datetime.now(UTC),
        )
        .order_by(OtpChallenge.created_at.desc())
        .limit(1)
    )


async def _deliver(db, challenge: OtpChallenge, code: str) -> None:
    try:
        from app.services.notify.service import NotifyService

        await NotifyService(db).emit_safe(
            OTP_EVENT,
            {
                "user_id": challenge.user_id,
                "challenge_id": challenge.id,
                "code": code,
                "expires_at": challenge.expires_at.isoformat(),
            },
        )
    except Exception:
        logger.debug("otp delivery failed", exc_info=True)
