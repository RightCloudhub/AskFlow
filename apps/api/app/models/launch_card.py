"""Launch Card: expected vs measured metrics for changes (PRD E21 / §12.2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

JSONType = JSON().with_variant(SQLITE_JSON(), "sqlite")


class LaunchCard(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "launch_cards"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True, nullable=False)
    # expected metrics e.g. {"faq_resolve_rate": 0.7, "unit_cost_delta": -0.2}
    expected_metrics: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    measured_metrics: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
