"""Warm handoff queue / claim / return (PRD §4.7)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.enums import ConversationStatus, HandoffStatus
from app.models.handoff import HandoffSession
from app.services.handoff.scope import filter_queue_by_team, merge_inbox

HTTP_NOT_FOUND = status.HTTP_404_NOT_FOUND
HTTP_FORBIDDEN = status.HTTP_403_FORBIDDEN
HTTP_CONFLICT = status.HTTP_409_CONFLICT


class HandoffService:
    OPEN = (HandoffStatus.QUEUED.value, HandoffStatus.CLAIMED.value)

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def enqueue(
        self,
        *,
        conversation_id: str,
        user_id: str,
        summary: str,
        intent: str = "handoff",
    ) -> HandoffSession:
        existing = await self.db.execute(
            select(HandoffSession).where(
                HandoffSession.conversation_id == conversation_id,
                HandoffSession.status.in_(self.OPEN),
            )
        )
        found = existing.scalar_one_or_none()
        if found is not None:
            return found

        try:
            async with self.db.begin_nested():
                session = HandoffSession(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    status=HandoffStatus.QUEUED.value,
                    summary=summary or "",
                    intent=intent or "handoff",
                )
                self.db.add(session)
                conv = await self.db.get(Conversation, conversation_id)
                if conv is not None:
                    conv.status = ConversationStatus.TRANSFERRED.value
                await self.db.flush()
            await self.db.refresh(session)
            return session
        except IntegrityError:
            existing = await self.db.execute(
                select(HandoffSession).where(
                    HandoffSession.conversation_id == conversation_id,
                    HandoffSession.status.in_(self.OPEN),
                )
            )
            found = existing.scalar_one_or_none()
            if found is None:
                raise
            return found

    async def list_queue(
        self,
        *,
        agent_id: str | None = None,
        agent_role: str | None = None,
    ) -> list[HandoffSession]:
        """Inbox: scoped queued items + sessions claimed by this agent."""
        result = await self.db.execute(
            select(HandoffSession)
            .where(HandoffSession.status == HandoffStatus.QUEUED.value)
            .order_by(HandoffSession.created_at.asc())
        )
        rows = list(result.scalars().all())
        if agent_id is None or agent_role == "admin":
            scoped = rows
        else:
            scoped = await filter_queue_by_team(self.db, rows, agent_id=agent_id)
        if agent_id is None:
            return scoped
        claimed = await self._claimed_by(agent_id)
        return merge_inbox(scoped, claimed)

    async def _claimed_by(self, agent_id: str) -> list[HandoffSession]:
        result = await self.db.execute(
            select(HandoffSession)
            .where(
                HandoffSession.status == HandoffStatus.CLAIMED.value,
                HandoffSession.claimed_by == agent_id,
            )
            .order_by(HandoffSession.claimed_at.desc())
        )
        return list(result.scalars().all())

    async def claim(
        self,
        handoff_id: str,
        agent_id: str,
        *,
        agent_role: str | None = None,
    ) -> HandoffSession:
        """Atomic claim: second concurrent claimer gets 409 (multi-worker safe)."""
        from sqlalchemy import update

        now = datetime.now(UTC)
        session = await self.db.get(HandoffSession, handoff_id)
        if session is None:
            raise HTTPException(status_code=HTTP_NOT_FOUND, detail="Handoff not found")
        if session.status == HandoffStatus.CLAIMED.value and session.claimed_by == agent_id:
            return session
        if session.status == HandoffStatus.CLAIMED.value and session.claimed_by != agent_id:
            raise HTTPException(status_code=HTTP_CONFLICT, detail="Already claimed")
        if session.status != HandoffStatus.QUEUED.value:
            raise HTTPException(status_code=HTTP_CONFLICT, detail="Handoff not claimable")

        if agent_role is not None and agent_role != "admin":
            await self._assert_in_scope(session, agent_id)

        cas = await self.db.execute(
            update(HandoffSession)
            .where(
                HandoffSession.id == handoff_id,
                HandoffSession.status == HandoffStatus.QUEUED.value,
            )
            .values(
                status=HandoffStatus.CLAIMED.value,
                claimed_by=agent_id,
                claimed_at=now,
            )
        )
        if cas.rowcount == 0:
            raise HTTPException(status_code=HTTP_CONFLICT, detail="Already claimed")
        session.status = HandoffStatus.CLAIMED.value
        session.claimed_by = agent_id
        session.claimed_at = now
        await self.db.flush()
        return session

    async def _assert_in_scope(self, session: HandoffSession, agent_id: str) -> None:
        result = await self.db.execute(
            select(HandoffSession).where(
                HandoffSession.status == HandoffStatus.QUEUED.value
            )
        )
        queued = list(result.scalars().all())
        visible = await filter_queue_by_team(self.db, queued, agent_id=agent_id)
        if not any(h.id == session.id for h in visible):
            raise HTTPException(status_code=HTTP_FORBIDDEN, detail="out_of_scope")

    async def return_to_ai(self, handoff_id: str, agent_id: str) -> HandoffSession:
        session = await self.db.get(HandoffSession, handoff_id)
        if session is None:
            raise HTTPException(status_code=HTTP_NOT_FOUND, detail="Handoff not found")
        if session.status != HandoffStatus.CLAIMED.value:
            raise HTTPException(status_code=HTTP_CONFLICT, detail="Handoff not claimed")
        if session.claimed_by != agent_id:
            raise HTTPException(status_code=HTTP_FORBIDDEN, detail="Not your handoff")
        session.status = HandoffStatus.RETURNED.value
        conv = await self.db.get(Conversation, session.conversation_id)
        if conv is not None:
            conv.status = ConversationStatus.ACTIVE.value
        await self.db.flush()
        await self.db.refresh(session)
        return session
