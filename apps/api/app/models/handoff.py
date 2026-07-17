"""Handoff session model — one open handoff per conversation (PRD §4.7 / §6.3)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import HandoffStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class HandoffSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "handoff_sessions"
    __table_args__ = (
        Index(
            "uq_handoff_open_conversation",
            "conversation_id",
            unique=True,
            sqlite_where=text("status IN ('queued', 'claimed')"),
            postgresql_where=text("status IN ('queued', 'claimed')"),
        ),
    )

    conversation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=HandoffStatus.QUEUED.value, index=True, nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Intent tag for skill-team queue scoping (PRD Wave B / §12.2)
    intent: Mapped[str] = mapped_column(String(64), default="", index=True, nullable=False)
    claimed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timed_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
