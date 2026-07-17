"""Channel identity: map external user keys to JIT guest Users + conversations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.conversation import Conversation
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.chat import ConversationCreate
from app.services.chat.session.service import ChatService
from app.utils.ids import new_id

EMAIL_DOMAIN = "channel.askflow.local"


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
    return user


async def open_channel_conversation(
    db: AsyncSession,
    *,
    user_id: str,
    title: str,
    external_chat_key: str | None = None,
) -> Conversation:
    """Reuse open conversation for same user+title when possible, else create."""
    if external_chat_key:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.title == title[:255])
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing is not None and existing.status == "active":
            meta = dict(existing.metadata_json or {})
            if meta.get("channel_chat_key") == external_chat_key:
                return existing
    conv = await ChatService(db).create_conversation(
        user_id,
        ConversationCreate(title=title[:255] or "channel"),
    )
    if external_chat_key:
        meta = dict(conv.metadata_json or {})
        meta["channel_chat_key"] = external_chat_key
        conv.metadata_json = meta
        await db.flush()
        await db.refresh(conv)
    return conv
