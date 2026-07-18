"""Priority-based ticket SLA scanner (PRD E1 / §12.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SLAState, TicketStatus
from app.models.ticket import Ticket

# priority → (first_response_minutes, resolve_minutes, warning_ratio of deadline)
DEFAULT_POLICIES: dict[str, tuple[int, int, float]] = {
    "urgent": (15, 120, 0.7),
    "high": (30, 240, 0.7),
    "medium": (120, 1440, 0.7),
    "low": (480, 4320, 0.7),
}


@dataclass
class SLAScanResult:
    ticket_id: str
    previous: str
    current: str
    reason: str  # first_response | resolve


class SLAEngine:
    def __init__(
        self,
        db: AsyncSession,
        *,
        now_fn: Callable[[], datetime] | None = None,
        policies: dict[str, tuple[int, int, float]] | None = None,
    ) -> None:
        self.db = db
        self.now_fn = now_fn or (lambda: datetime.now(UTC))
        self.policies = policies or DEFAULT_POLICIES

    def _policy(self, priority: str) -> tuple[int, int, float]:
        return self.policies.get(priority, self.policies["medium"])

    def evaluate_ticket(self, ticket: Ticket, now: datetime | None = None) -> tuple[str, str | None]:
        """Return (state, reason) without mutating."""
        now = now or self.now_fn()
        if ticket.status in {TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value}:
            return SLAState.OK.value, None

        fr_min, resolve_min, warn_ratio = self._policy(ticket.priority)
        created = ticket.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)

        # first response SLA if not yet responded
        if ticket.first_responded_at is None:
            fr_deadline = created + timedelta(minutes=fr_min)
            fr_warn = created + timedelta(minutes=int(fr_min * warn_ratio))
            if now >= fr_deadline:
                return SLAState.BREACHED.value, "first_response"
            if now >= fr_warn:
                return SLAState.WARNING.value, "first_response"

        # resolve SLA for open tickets
        resolve_deadline = created + timedelta(minutes=resolve_min)
        resolve_warn = created + timedelta(minutes=int(resolve_min * warn_ratio))
        if now >= resolve_deadline:
            return SLAState.BREACHED.value, "resolve"
        if now >= resolve_warn:
            return SLAState.WARNING.value, "resolve"
        return SLAState.OK.value, None

    async def scan(self) -> list[SLAScanResult]:
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.status.in_([TicketStatus.PENDING.value, TicketStatus.PROCESSING.value])
            )
        )
        tickets = list(result.scalars().all())
        now = self.now_fn()
        changes: list[SLAScanResult] = []
        for t in tickets:
            prev = t.sla_state or SLAState.OK.value
            state, reason = self.evaluate_ticket(t, now)
            # Sticky breach: never downgrade BREACHED → warning/ok (audit trail)
            if prev == SLAState.BREACHED.value and state != SLAState.BREACHED.value:
                continue
            if state == prev:
                continue
            t.sla_state = state
            if state == SLAState.WARNING.value and t.sla_warning_at is None:
                t.sla_warning_at = now
            if state == SLAState.BREACHED.value and t.sla_breached_at is None:
                t.sla_breached_at = now
            changes.append(
                SLAScanResult(
                    ticket_id=t.id,
                    previous=prev,
                    current=state,
                    reason=reason or "unknown",
                )
            )
        await self.db.flush()
        return changes
