"""Per-event failures defer only that event and retain later eligible work."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.commerce.core.event_retry import EventRetry
from app.services.outbox.store import emit, pending, record_failure
from .helpers import transaction


@pytest.mark.asyncio
async def test_retry_waits_without_blocking_new_events(mall_runtime):
    async def arrange(db):
        first = await emit(db, aggregate="test", aggregate_id="one", event_type="mall.test", payload={})
        second = await emit(db, aggregate="test", aggregate_id="two", event_type="mall.test", payload={})
        await record_failure(db, first, "ConnectionError")
        return first.id, second.id

    first, second = await transaction(mall_runtime, arrange)
    async with mall_runtime.sessions() as db:
        assert [row.id for row in await pending(db, limit=10, max_attempts=5)] == [second]
        await db.execute(update(EventRetry).where(EventRetry.event_id == first).values(
            next_attempt_at=datetime.now(UTC) - timedelta(seconds=1)))
        await db.commit()
        assert [row.id for row in await pending(db, limit=10, max_attempts=5)] == [first, second]
