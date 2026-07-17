"""Persisted Agent run for admin replay (PRD S-08 / E22)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AgentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    route: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    refused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flags: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    steps: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    cost_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
