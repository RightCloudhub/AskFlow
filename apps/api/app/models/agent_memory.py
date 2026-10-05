"""Scoped memory records shared by facts, timeline references and experience hints."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin

SCOPE_LENGTH = 128
KIND_LENGTH = 32
KEY_LENGTH = 255


class AgentMemory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "agent_memories"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "customer_id", "kind", "key", name="uq_agent_memory_scope_kind_key"
        ),
    )

    organization_id: Mapped[str] = mapped_column(String(SCOPE_LENGTH), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(SCOPE_LENGTH), nullable=False)
    kind: Mapped[str] = mapped_column(String(KIND_LENGTH), nullable=False)
    key: Mapped[str] = mapped_column(String(KEY_LENGTH), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(SCOPE_LENGTH), nullable=False)
    verification: Mapped[str] = mapped_column(String(KIND_LENGTH), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
