"""Channel identity: map external user keys to JIT guest Users + conversations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.channel_identity import ASSURANCE_CHANNEL_VERIFIED, ChannelIdentity
from app.models.conversation import Conversation
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.chat import ConversationCreate
from app.services.chat.session.service import ChatService
from app.utils.ids import new_id

EMAIL_DOMAIN = "channel.askflow.local"
TITLE_LENGTH = 255


async def ensure_channel_user(
    db: AsyncSession,
    *,
    channel: str,
    external_id: str,
) -> User:
    """JIT provision a user for IM/widget-style channels (single-tenant)."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in external_id)[:48]
    email = f"{channel}.{safe}@{EMAIL_DOMAIN}"[:255]
    username = f"{channel}_{safe}"[:64]
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        await _ensure_channel_identity(db, channel=channel, external_id=external_id, user_id=user.id)
        return user
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(new_id() + channel),
        role=UserRole.USER.value,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await _ensure_channel_identity(db, channel=channel, external_id=external_id, user_id=user.id)
    return user


async def _ensure_channel_identity(db, *, channel: str, external_id: str, user_id: str) -> None:
    existing = await db.scalar(
        select(ChannelIdentity)
        .where(
            ChannelIdentity.channel == channel,
            ChannelIdentity.channel_user_id == external_id,
        )
        .limit(1)
    )
    if existing is not None:
        return
    db.add(
        ChannelIdentity(
            channel=channel,
            channel_user_id=external_id,
            user_id=user_id,
            assurance_level=ASSURANCE_CHANNEL_VERIFIED,
        )
    )
    await db.flush()


async def open_channel_conversation(
    db: AsyncSession,
    *,
    user_id: str,
    title: str,
    external_chat_key: str | None = None,
    channel: str | None = None,
) -> Conversation:
    """Reuse open conversation for same user+title when possible, else create."""
    if external_chat_key:
        existing = await _find_reusable(
            db, user_id=user_id, title=title, external_chat_key=external_chat_key
        )
        if existing is not None:
            await _apply_channel_meta(
                db, existing, external_chat_key=external_chat_key, channel=channel
            )
            return existing
    conv = await ChatService(db).create_conversation(
        user_id,
        ConversationCreate(title=title[:TITLE_LENGTH] or "channel"),
    )
    await _apply_channel_meta(db, conv, external_chat_key=external_chat_key, channel=channel)
    return conv


async def _find_reusable(
    db, *, user_id: str, title: str, external_chat_key: str
) -> Conversation | None:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .where(Conversation.title == title[:TITLE_LENGTH])
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing is None or existing.status != "active":
        return None
    if (existing.metadata_json or {}).get("channel_chat_key") != external_chat_key:
        return None
    return existing


async def _apply_channel_meta(
    db, conv, *, external_chat_key: str | None, channel: str | None
) -> None:
    if not external_chat_key and not channel:
        return
    meta = dict(conv.metadata_json or {})
    if external_chat_key:
        meta["channel_chat_key"] = external_chat_key
    if channel:
        meta["channel"] = channel
    if meta == (conv.metadata_json or {}):
        return
    conv.metadata_json = meta
    await db.flush()
    await db.refresh(conv)
