from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.core.deps import DbSession, require_admin
from app.middleware.metrics import SLA_EVENTS_TOTAL
from app.models.enums import NotifyEvent
from app.models.ticket import Ticket
from app.models.user import User
from app.services.notify.service import NotifyService
from app.services.ticket.sla.engine import SLAEngine

router = APIRouter(dependencies=[Depends(require_admin)])
DEFAULT_SLA_TICKET_LIMIT = 50
MAX_SLA_TICKET_LIMIT = 200


@router.get("/status")
async def sla_status(
    db: DbSession,
    _user: User = Depends(require_admin),
    limit: int = Query(default=DEFAULT_SLA_TICKET_LIMIT, ge=1, le=MAX_SLA_TICKET_LIMIT),
) -> dict:
    """Open tickets with non-ok SLA + aggregate counts for Admin UI."""
    by_state = await db.execute(
        select(Ticket.sla_state, func.count()).group_by(Ticket.sla_state)
    )
    counts = {str(s or "ok"): int(n or 0) for s, n in by_state.all()}
    result = await db.execute(
        select(Ticket)
        .where(Ticket.sla_state.in_(["warning", "breached"]))
        .order_by(Ticket.updated_at.desc())
        .limit(limit)
    )
    rows = list(result.scalars().all())
    return {
        "counts": counts,
        "tickets": [
            {
                "id": t.id,
                "title": t.title,
                "priority": t.priority,
                "status": t.status,
                "sla_state": t.sla_state,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ],
    }


@router.post("/scan")
async def scan_sla(db: DbSession, _user: User = Depends(require_admin)) -> dict:
    engine = SLAEngine(db)
    changes = await engine.scan()
    notify = NotifyService(db)
    for ch in changes:
        event = (
            NotifyEvent.SLA_BREACHED.value
            if ch.current == "breached"
            else NotifyEvent.SLA_WARNING.value
        )
        SLA_EVENTS_TOTAL.labels(state=ch.current, reason=ch.reason).inc()
        await notify.emit_safe(
            event,
            {
                "ticket_id": ch.ticket_id,
                "previous": ch.previous,
                "current": ch.current,
                "reason": ch.reason,
            },
        )
    return {
        "scanned_changes": len(changes),
        "changes": [
            {
                "ticket_id": c.ticket_id,
                "previous": c.previous,
                "current": c.current,
                "reason": c.reason,
            }
            for c in changes
        ],
    }
