"""Shared IM channel → ChatService pipeline (Feishu / WeCom / DingTalk)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.metrics import CHAT_TURNS
from app.services.audit.logger.service import AuditService
from app.services.channels.identity import ensure_channel_user, open_channel_conversation
from app.services.chat.session.service import ChatService

TITLE_MAX = 40


@dataclass
class ChannelTurnResult:
    answer: str
    run_id: str
    route: str
    conversation_id: str
    user_id: str


async def run_channel_turn(
    db: AsyncSession,
    *,
    channel: str,
    external_user_id: str,
    text: str,
    chat_key: str | None = None,
    title_prefix: str | None = None,
) -> ChannelTurnResult:
    user = await ensure_channel_user(db, channel=channel, external_id=external_user_id)
    prefix = title_prefix or channel
    title = f"{prefix}:{external_user_id[:12]}"[:TITLE_MAX]
    conv = await open_channel_conversation(
        db,
        user_id=user.id,
        title=title,
        external_chat_key=chat_key or external_user_id,
    )
    _user_msg, asst_msg, result = await ChatService(db).handle_user_message(
        conv.id, user.id, text
    )
    CHAT_TURNS.labels(route=result.route, intent=result.intent or "none").inc()
    await AuditService(db).log(
        action=f"{channel}.message",
        resource_type="conversation",
        resource_id=conv.id,
        actor_id=user.id,
        detail={"external_id": external_user_id, "run_id": result.run_id, "route": result.route},
    )
    return ChannelTurnResult(
        answer=asst_msg.content,
        run_id=result.run_id,
        route=result.route,
        conversation_id=conv.id,
        user_id=user.id,
    )
