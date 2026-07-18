"""Unified ticket creation entry — no bypass inserts (PRD §6.3)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TicketPriority, TicketStatus
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate


class TicketRepository:
    OPEN_STATUSES = (TicketStatus.PENDING.value, TicketStatus.PROCESSING.value)

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_or_get_open(self, user_id: str, payload: TicketCreate) -> tuple[Ticket, bool]:
        """Return (ticket, created). Concurrent creates converge on same open ticket.

        Prefer conversation+type match (agent pipeline) before title uniqueness.
        """
        found = await self._find_open(user_id, payload)
        if found is not None:
            return found, False

        try:
            async with self.db.begin_nested():
                ticket = Ticket(
                    user_id=user_id,
                    conversation_id=payload.conversation_id,
                    type=payload.type,
                    status=TicketStatus.PENDING.value,
                    priority=payload.priority or TicketPriority.MEDIUM.value,
                    title=payload.title,
                    description=payload.description,
                    content=payload.content or {},
                )
                self.db.add(ticket)
                await self.db.flush()
            await self.db.refresh(ticket)
            return ticket, True
        except IntegrityError:
            found = await self._find_open(user_id, payload)
            if found is None:
                raise
            return found, False

    async def _find_open(self, user_id: str, payload: TicketCreate) -> Ticket | None:
        ticket_type = payload.type or "user_created"
        if payload.conversation_id:
            by_conv = await self.db.execute(
                select(Ticket).where(
                    Ticket.user_id == user_id,
                    Ticket.conversation_id == payload.conversation_id,
                    Ticket.type == ticket_type,
                    Ticket.status.in_(self.OPEN_STATUSES),
                )
            )
            hit = by_conv.scalar_one_or_none()
            if hit is not None:
                return hit
        by_title = await self.db.execute(
            select(Ticket).where(
                Ticket.user_id == user_id,
                Ticket.title == payload.title,
                Ticket.status.in_(self.OPEN_STATUSES),
            )
        )
        return by_title.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(self, *, status: str | None = None) -> list[Ticket]:
        stmt = select(Ticket).order_by(Ticket.created_at.desc())
        if status:
            stmt = stmt.where(Ticket.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, ticket_id: str) -> Ticket | None:
        result = await self.db.execute(select(Ticket).where(Ticket.id == ticket_id))
        return result.scalar_one_or_none()

    async def update_status(
        self,
        ticket: Ticket,
        *,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        description: str | None = None,
    ) -> Ticket:
        if status is not None:
            ticket.status = status
            if status == TicketStatus.RESOLVED.value:
                ticket.resolved_at = datetime.now(UTC)
        if priority is not None:
            ticket.priority = priority
        if assignee is not None:
            ticket.assignee = assignee
        if description is not None:
            ticket.description = description
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket
