"""Operational intent → route mapping (hot-config, PRD §4.3)."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class IntentConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "intent_configs"

    intent: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    route: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    min_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
