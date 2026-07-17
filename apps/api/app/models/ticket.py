"""Ticket model with open-ticket uniqueness red-line (PRD §4.6 / §6.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.enums import TicketPriority, TicketStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

JSONType = JSON().with_variant(SQLITE_JSON(), "sqlite")


class Ticket(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tickets"
    __table_args__ = (
        # Partial unique: one open ticket per (user_id, title)
        Index(
            "uq_ticket_open_user_title",
            "user_id",
            "title",
            unique=True,
            sqlite_where=text("status IN ('pending', 'processing')"),
            postgresql_where=text("status IN ('pending', 'processing')"),
        ),
    )

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    type: Mapped[str] = mapped_column(String(64), default="user_created", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=TicketStatus.PENDING.value, index=True, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(32), default=TicketPriority.MEDIUM.value, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SLA fields (PRD §12.2 / Wave A)
    first_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_state: Mapped[str] = mapped_column(String(32), default="ok", index=True, nullable=False)
    sla_warning_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    team_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
