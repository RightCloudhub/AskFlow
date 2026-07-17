"""Persisted cost ledger entries for admin aggregates (PRD §4.17 / §12.2)."""

from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CostLedgerEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cost_ledger_entries"

    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
