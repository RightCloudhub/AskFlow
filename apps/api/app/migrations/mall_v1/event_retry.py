"""Frozen retry extension, independent of live outbox/commerce models."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.migrations.mall_v1.base import Base


class EventRetry(Base):
    __tablename__ = "mall_event_retries"
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("outbox.id", ondelete="CASCADE"), primary_key=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
