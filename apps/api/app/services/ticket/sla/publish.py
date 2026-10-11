"""Announce committed SLA transitions (webhook + metric). Call only after ``db.commit()`` (D-09)."""

from __future__ import annotations

from collections.abc import Iterable

from app.middleware.metrics import SLA_EVENTS_TOTAL
from app.models.enums import NotifyEvent
from app.services.notify.service import NotifyService
from app.services.ticket.sla.engine import SLAScanResult

UNKNOWN_REASON = "unknown"


async def publish_sla_changes(notify: NotifyService, changes: Iterable[SLAScanResult]) -> None:
    for ch in changes:
        event = (
            NotifyEvent.SLA_BREACHED.value
            if ch.current == "breached"
            else NotifyEvent.SLA_WARNING.value
        )
        SLA_EVENTS_TOTAL.labels(state=ch.current, reason=ch.reason or UNKNOWN_REASON).inc()
        await notify.emit_safe(
            event,
            {
                "ticket_id": ch.ticket_id,
                "previous": ch.previous,
                "current": ch.current,
                "reason": ch.reason,
            },
        )
