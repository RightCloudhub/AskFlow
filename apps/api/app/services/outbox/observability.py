"""Read-only outbox aggregates for commerce operational dashboards."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models.outbox import OutboxEvent

CALLBACK_WINDOW_MINUTES = 5


async def commerce_snapshot(db):
    mall = OutboxEvent.event_type.startswith("mall.")
    backlog = await db.scalar(select(func.count()).select_from(OutboxEvent).where(
        mall, OutboxEvent.published_at.is_(None)))
    recent = datetime.now(UTC) - timedelta(minutes=CALLBACK_WINDOW_MINUTES)
    callbacks = await db.scalar(select(func.count()).select_from(OutboxEvent).where(
        OutboxEvent.event_type == "mall.payment.callback_rejected", OutboxEvent.created_at >= recent))
    events = await db.execute(select(OutboxEvent.event_type, func.count()).where(mall)
                             .group_by(OutboxEvent.event_type))
    return {"backlog": backlog, "callbacks_rejected": callbacks, "events": dict(events.all())}
