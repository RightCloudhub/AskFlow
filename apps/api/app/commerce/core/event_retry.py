"""Retry scheduling extends outbox without changing its existing envelope or columns."""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, or_, update
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.repository import insert_once
from app.core.config import get_settings
from app.core.database import Base
from app.models.outbox import OutboxEvent


class EventRetry(Base):
    __tablename__ = "mall_event_retries"
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("outbox.id", ondelete="CASCADE"), primary_key=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


def ready(statement):
    return statement.outerjoin(EventRetry, EventRetry.event_id == OutboxEvent.id).where(
        or_(EventRetry.event_id.is_(None), EventRetry.next_attempt_at <= datetime.now(UTC)))


async def schedule(db, event):
    settings = get_settings()
    delay = min(settings.mall_event_retry_max_seconds,
                settings.mall_event_retry_base_seconds * (2 ** event.attempts))
    due = datetime.now(UTC) + timedelta(seconds=delay + random.random() * delay)
    await insert_once(db, EventRetry, values={"event_id": event.id, "next_attempt_at": due}, unique=["event_id"])
    await db.execute(update(EventRetry).where(EventRetry.event_id == event.id).values(next_attempt_at=due))
