"""Conversation and message persistence (PRD §4.5)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole
from app.plugins.types import ChatTurnContext
from app.schemas.chat import ConversationCreate, ConversationUpdate
from app.services.agent.pipeline.runner import MessagePipeline, PipelineResult
from app.services.chat.side_effects.apply import apply_side_effects
from app.utils.merge import merge_patch

TITLE_DEFAULTS = frozenset({"新会话", "New chat"})
TITLE_MAX = 40


class ChatService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_conversation(self, user_id: str, payload: ConversationCreate) -> Conversation:
        conv = Conversation(user_id=user_id, title=payload.title)
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def list_conversations(self, user_id: str) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_conversation(self, conversation_id: str, user_id: str | None = None) -> Conversation:
        conv = await self.db.get(Conversation, conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if user_id is not None and conv.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not your conversation")
        return conv

    async def update_conversation(
        self, conversation_id: str, user_id: str, payload: ConversationUpdate
    ) -> Conversation:
        conv = await self.get_conversation(conversation_id, user_id)
        if payload.title is not None:
            conv.title = payload.title
        if payload.status is not None:
            # Block user self-escalation to transferred / arbitrary statuses
            allowed = {"active", "closed"}
            if payload.status not in allowed:
                raise HTTPException(status_code=400, detail="invalid_status")
            conv.status = payload.status
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def list_messages(self, conversation_id: str, user_id: str) -> list[Message]:
        await self.get_conversation(conversation_id, user_id)
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation_id: str,
        *,
        role: str,
        content: str,
        meta: dict[str, Any] | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            meta=meta or {},
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def handle_user_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
    ) -> tuple[Message, Message, PipelineResult]:
        conv = await self.get_conversation(conversation_id, user_id)
        user_msg = await self.add_message(
            conversation_id,
            role=MessageRole.USER.value,
            content=content,
        )

        history_rows = await self.list_messages(conversation_id, user_id)
        history = [
            {"role": m.role, "content": m.content}
            for m in history_rows
            if m.id != user_msg.id
        ]

        pipeline = MessagePipeline(self.db)
        result = await pipeline.handle(
            content,
            history=history,
            metadata=conv.metadata_json or {},
            conversation_status=conv.status,
        )

        if result.metadata_patch:
            conv.metadata_json = merge_patch(conv.metadata_json or {}, result.metadata_patch)

        se = await apply_side_effects(
            dict(result.side_effects or {}),
            ChatTurnContext(
                db=self.db,
                conversation_id=conversation_id,
                user_id=user_id,
                content=content,
                intent=result.intent,
                route=result.route,
                refused=result.refused,
                verification=result.verification if isinstance(result.verification, dict) else None,
                run_id=result.run_id,
                cost=result.cost if isinstance(result.cost, dict) else None,
                flags=list(result.flags or []),
            ),
        )
        result.side_effects = se

        assistant_meta = {
            "run_id": result.run_id,
            "trace_id": result.trace_id,
            "route": result.route,
            "intent": result.intent,
            "confidence": result.confidence,
            "answer_confidence": result.answer_confidence,
            "sources": result.sources,
            "flags": result.flags,
            "verification": result.verification,
            "rewrite": result.rewrite,
            "refused": result.refused,
            "side_effects": se,
            "cost": result.cost,
            "models": result.cost.get("entries") if isinstance(result.cost, dict) else [],
        }
        assistant_msg = await self.add_message(
            conversation_id,
            role=MessageRole.ASSISTANT.value,
            content=result.answer,
            meta=assistant_meta,
        )

        if conv.title in TITLE_DEFAULTS and content:
            conv.title = content[:TITLE_MAX]

        await self.db.flush()
        return user_msg, assistant_msg, result
