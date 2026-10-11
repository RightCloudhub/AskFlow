"""Handoff timeout sweeper: queued too long → high-priority ticket + return AI (PRD §4.7.5).

Multi-worker safe: claim rows with status transition only if still queued
(compare-and-set) to avoid double-ticket under concurrent sweepers.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.middleware.metrics import HANDOFF_TIMEOUT_TOTAL
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus, HandoffStatus, NotifyEvent, TicketPriority
from app.models.handoff import HandoffSession
from app.schemas.ticket import TicketCreate
from app.services.notify.service import NotifyService
from app.services.ticket.repository.service import TicketRepository

CONVERSATION_TAG_LEN = 8


class HandoffTimeoutSweeper:
    """Expire queued handoffs, then — only after the caller commits — announce them (D-09)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def sweep(self) -> list[dict]:
        cutoff = datetime.now(UTC) - timedelta(seconds=self.settings.handoff_timeout_seconds)
        result = await self.db.execute(
            select(HandoffSession).where(
                HandoffSession.status == HandoffStatus.QUEUED.value,
                HandoffSession.created_at <= cutoff,
            )
        )
        outcomes = [await self._expire(s) for s in result.scalars().all()]
        await self.db.flush()
        return [o for o in outcomes if o is not None]

    async def publish(self, outcomes: list[dict]) -> None:
        """Webhook + metric for committed timeouts. Never call before ``db.commit()``."""
        notify = NotifyService(self.db)
        for outcome in outcomes:
            await notify.emit_safe(
                NotifyEvent.HANDOFF_TIMEOUT.value,
                {k: outcome[k] for k in ("handoff_id", "ticket_id", "conversation_id", "user_id")},
            )
            HANDOFF_TIMEOUT_TOTAL.inc()

    async def _expire(self, session: HandoffSession) -> dict | None:
        # CAS: only one worker wins the timeout transition
        cas = await self.db.execute(
            update(HandoffSession)
            .where(
                HandoffSession.id == session.id,
                HandoffSession.status == HandoffStatus.QUEUED.value,
            )
            .values(status=HandoffStatus.TIMED_OUT.value, timed_out_at=datetime.now(UTC))
        )
        if cas.rowcount == 0:
            return None
        ticket, created = await TicketRepository(self.db).create_or_get_open(
            session.user_id,
            TicketCreate(
                title=f"转人工超时: {session.conversation_id[:CONVERSATION_TAG_LEN]}",
                description=session.summary or "handoff timeout",
                type="handoff_timeout",
                priority=TicketPriority.HIGH.value,
                conversation_id=session.conversation_id,
                content={"handoff_id": session.id},
            ),
        )
        conv = await self.db.get(Conversation, session.conversation_id)
        conv.status = ConversationStatus.ACTIVE.value
        return {
            "handoff_id": session.id,
            "ticket_id": ticket.id,
            "ticket_created": created,
            "conversation_id": session.conversation_id,
            "user_id": session.user_id,
        }
