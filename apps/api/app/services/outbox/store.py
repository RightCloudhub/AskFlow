"""Outbox persistence: same-transaction emits, ordered pending reads (arch §4.5)."""

from datetime import UTC, datetime

from sqlalchemy import select, update

from app.models.outbox import OutboxEvent

ERROR_LENGTH = 255

EVENT_TASK_RESULT = "task.result"
EVENT_CONFIRMATION_REQUESTED = "confirmation.requested"


async def emit(db, *, aggregate: str, aggregate_id: str, event_type: str, payload: dict) -> OutboxEvent:
    row = OutboxEvent(
        aggregate=aggregate,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(row)
    await db.flush()
    return row


async def pending(db, *, limit: int, max_attempts: int, excluded=()) -> list[OutboxEvent]:
    from app.plugins.runtime import get_app_context

    ctx = get_app_context()
    enabled = ctx is not None and ctx.enabled("mall_core")
    domain_filter = True if enabled else ~OutboxEvent.event_type.startswith("mall.")
    statement = select(OutboxEvent)
    if enabled:
        from app.commerce.core.event_retry import ready

        statement = ready(statement)
    return list(await db.scalars(statement
            .where(OutboxEvent.published_at.is_(None), OutboxEvent.attempts < max_attempts, domain_filter)
            .where(OutboxEvent.id.not_in(excluded))
            .order_by(OutboxEvent.id)
            .limit(limit)
            .with_for_update(skip_locked=True, of=OutboxEvent)))


async def mark_published(db, event: OutboxEvent) -> None:
    await db.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event.id)
        .values(published_at=datetime.now(UTC), last_error=None)
        .execution_options(synchronize_session=False)
    )


async def record_failure(db, event: OutboxEvent, error: str) -> None:
    if event.event_type.startswith("mall."):
        from app.commerce.core.event_retry import schedule

        await schedule(db, event)
    await db.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event.id)
        .values(attempts=OutboxEvent.attempts + 1, last_error=error[:ERROR_LENGTH])
        .execution_options(synchronize_session=False)
    )
