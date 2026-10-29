"""Transactional outbox: state changes and their events commit together (arch §4.5)."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.migrations.mall_v1.base import Base
from app.migrations.mall_v1.legacy_mixins import TimestampMixin

ID_LENGTH = 36
NAME_LENGTH = 128
ERROR_LENGTH = 255


class OutboxEvent(Base, TimestampMixin):
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aggregate: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(ID_LENGTH), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(ERROR_LENGTH), nullable=True)
