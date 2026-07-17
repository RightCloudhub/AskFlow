"""Audit log with optional masked payload (PRD §4.11)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

JSONType = JSON().with_variant(SQLITE_JSON(), "sqlite")


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    actor_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
