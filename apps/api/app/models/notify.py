"""Notification delivery log (best-effort, PRD E2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

JSONType = JSON().with_variant(SQLITE_JSON(), "sqlite")


class NotificationLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notification_logs"

    event: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(32), default="webhook", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="sent", nullable=False)
    target: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
