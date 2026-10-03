"""Conversation and message persistence (PRD §4.5)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole
from app.schemas.chat import ConversationCreate, ConversationUpdate
from app.services.agent.pipeline.context import PipelineResult

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if user_id is not None and conv.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your conversation")
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
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_status")
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
        *,
        attachments: list | None = None,
        bot_id: str | None = None,
        locale: str | None = None,
    ) -> tuple[Message, Message, PipelineResult]:
        from app.services.chat.session.turn import ChatInput, ChatTurn

        return await ChatTurn(self, ChatInput(
            conversation_id=conversation_id, user_id=user_id, content=content,
            attachments=attachments, bot_id=bot_id, locale=locale,
        )).run()
