"""Trusted AskFlow events enter the same transactional mall notification outbox."""

from datetime import UTC, datetime
from uuid import uuid4

from app.core.trace import get_trace_id
from app.plugins.runtime import get_app_context
from app.services.outbox.store import emit


async def ticket_changed(db, ticket):
    await event(db, aggregate="ticket", aggregate_id=ticket.id,
        event_type="mall.support.ticket_changed", payload={"user_id": ticket.user_id,
            "ticket_id": ticket.id, "status": ticket.status})


async def event(db, *, aggregate, aggregate_id, event_type, payload):
    ctx = get_app_context()
    if ctx is None or not ctx.enabled("mall_notify"):
        return
    await emit(db, aggregate=aggregate, aggregate_id=aggregate_id, event_type=event_type, payload={
        "event_id": str(uuid4()), "event_type": event_type, "tenant_id": "deployment",
        "occurred_at": datetime.now(UTC).isoformat(), "trace_id": get_trace_id(),
        "aggregate": {"type": aggregate, "id": aggregate_id, "version": 0}, "payload": payload})
