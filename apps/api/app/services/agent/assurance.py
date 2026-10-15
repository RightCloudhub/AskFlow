"""Identity assurance levels: L0 anonymous, L1 channel-verified, L2 authenticated (arch §4.2)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.channel_identity import ChannelIdentity
from app.models.user import User

LEVEL_ANONYMOUS = 0
LEVEL_CHANNEL_VERIFIED = 1
LEVEL_AUTHENTICATED = 2
GUEST_EMAIL_DOMAIN = "guest.askflow.local"
ASSURANCE_META_KEY = "assurance_level"
ASSURANCE_EXPIRES_META_KEY = "assurance_expires_at"


async def user_assurance(db, user_id: str) -> int:
    """Resolve the principal's base assurance from its account and channel links."""
    user = await db.get(User, user_id)
    if user is not None and user.email and user.email.endswith(GUEST_EMAIL_DOMAIN):
        return LEVEL_ANONYMOUS
    identity = await db.scalar(
        select(ChannelIdentity).where(ChannelIdentity.user_id == user_id).limit(1)
    )
    if identity is not None:
        return identity.assurance_level
    return LEVEL_AUTHENTICATED


def conversation_assurance(conversation, base: int) -> int:
    """Apply a time-boxed elevation stored on the conversation (step-up result)."""
    meta = conversation.metadata_json or {}
    level = meta.get(ASSURANCE_META_KEY)
    expires = meta.get(ASSURANCE_EXPIRES_META_KEY)
    if not isinstance(level, int) or not isinstance(expires, str) or not _after_now(expires):
        return base
    return max(base, level)


def elevation_patch(level: int, ttl_seconds: int) -> dict:
    return {
        ASSURANCE_META_KEY: level,
        ASSURANCE_EXPIRES_META_KEY: (
            datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        ).isoformat(),
    }


def _after_now(value: str) -> bool:
    try:
        return datetime.fromisoformat(value) > datetime.now(UTC)
    except ValueError:
        return False
