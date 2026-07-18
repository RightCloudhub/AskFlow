"""Staff message ops for claimed handoff sessions (PRD §4.7)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.enums import HandoffStatus, MessageRole
from app.models.handoff import HandoffSession
from app.services.chat.session.service import ChatService

HTTP_FORBIDDEN = status.HTTP_403_FORBIDDEN
HTTP_CONFLICT = status.HTTP_409_CONFLICT
HTTP_NOT_FOUND = status.HTTP_404_NOT_FOUND


class HandoffStaffOps:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.chat = ChatService(db)

    async def get_session(self, handoff_id: str) -> HandoffSession:
        session = await self.db.get(HandoffSession, handoff_id)
        if session is None:
            raise HTTPException(status_code=HTTP_NOT_FOUND, detail="Handoff not found")
        return session

    async def require_claim_access(
        self,
        handoff_id: str,
        agent_id: str,
        *,
        agent_role: str | None = None,
    ) -> HandoffSession:
        session = await self.get_session(handoff_id)
        if agent_role == "admin":
            return session
        if session.status != HandoffStatus.CLAIMED.value:
            raise HTTPException(status_code=HTTP_CONFLICT, detail="Handoff not claimed")
        if session.claimed_by != agent_id:
            raise HTTPException(status_code=HTTP_FORBIDDEN, detail="Not your handoff")
        return session

    async def list_messages(
        self,
        handoff_id: str,
        agent_id: str,
        *,
        agent_role: str | None = None,
    ) -> list[Message]:
        session = await self.require_claim_access(
            handoff_id, agent_id, agent_role=agent_role
        )
        conv = await self.db.get(Conversation, session.conversation_id)
        if conv is None:
            raise HTTPException(status_code=HTTP_NOT_FOUND, detail="Conversation not found")
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == session.conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def staff_reply(
        self,
        handoff_id: str,
        agent_id: str,
        content: str,
        *,
        agent_role: str | None = None,
    ) -> Message:
        text = (content or "").strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="empty_content"
            )
        session = await self.require_claim_access(
            handoff_id, agent_id, agent_role=agent_role
        )
        return await self.chat.add_message(
            session.conversation_id,
            role=MessageRole.STAFF.value,
            content=text,
            meta={"agent_id": agent_id, "handoff_id": handoff_id},
        )
