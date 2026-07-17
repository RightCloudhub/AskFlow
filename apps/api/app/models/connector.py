"""Config-driven HTTP business connectors (PRD E6 / §12.2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

JSONType = JSON().with_variant(SQLITE_JSON(), "sqlite")


class ConnectorConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "connector_configs"

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    method: Mapped[str] = mapped_column(String(16), default="GET", nullable=False)
    path_template: Mapped[str] = mapped_column(String(512), default="/", nullable=False)
    auth_header: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    headers: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
