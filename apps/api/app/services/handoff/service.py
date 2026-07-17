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

        try:
            await self.db.flush()
            await self.db.refresh(session)
            return session
        except IntegrityError:
            await self.db.rollback()
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
        """List queued handoffs; non-admin agents are filtered by team intent_scope.

        Rules:
        - admin (or no agent_id): full queue
        - agent with no team membership: empty queue
        - agent whose teams include empty intent_scope: full queue (catch-all team)
        - otherwise: only handoffs whose intent is in the union of team scopes
        """
        result = await self.db.execute(
            select(HandoffSession)
            .where(HandoffSession.status == HandoffStatus.QUEUED.value)
            .order_by(HandoffSession.created_at.asc())
        )
        rows = list(result.scalars().all())
        if agent_id is None or agent_role == "admin":
            return rows

        from app.services.team.service import TeamService

        team_svc = TeamService(self.db)
        team_ids = await team_svc.user_team_ids(agent_id)
        if not team_ids:
            return []

        scopes = await team_svc.team_intent_scopes(agent_id)
        # empty string in scopes means a catch-all team (intent_scope blank)
        teams = await team_svc.list_teams()
        member_teams = [t for t in teams if t.id in team_ids]
        if any(not (t.intent_scope or "").strip() for t in member_teams):
            return rows
        if not scopes:
            return []
        return [h for h in rows if (h.intent or "handoff") in scopes]

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
        # Idempotent re-claim by same agent
        session = await self.db.get(HandoffSession, handoff_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Handoff not found")
        if session.status == HandoffStatus.CLAIMED.value and session.claimed_by == agent_id:
            return session
        if session.status == HandoffStatus.CLAIMED.value and session.claimed_by != agent_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already claimed")
        if session.status != HandoffStatus.QUEUED.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Handoff not claimable")

        # Enforce same team intent_scope as list_queue (M4). Skip when role omitted (internal/tests).
        if agent_role is not None and agent_role != "admin":
            visible = await self.list_queue(agent_id=agent_id, agent_role=agent_role)
            if not any(h.id == handoff_id for h in visible):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="out_of_scope")

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
            # lost race
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already claimed")
        # Sync identity map after bulk CAS (refresh alone can lag on some dialects)
        session.status = HandoffStatus.CLAIMED.value
        session.claimed_by = agent_id
        session.claimed_at = now
        await self.db.flush()
        return session

    async def return_to_ai(self, handoff_id: str, agent_id: str) -> HandoffSession:
        session = await self.db.get(HandoffSession, handoff_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Handoff not found")
        if session.claimed_by != agent_id:
            raise HTTPException(status_code=403, detail="Not your handoff")
        session.status = HandoffStatus.RETURNED.value
        conv = await self.db.get(Conversation, session.conversation_id)
        if conv is not None:
            conv.status = ConversationStatus.ACTIVE.value
        await self.db.flush()
        await self.db.refresh(session)
        return session
