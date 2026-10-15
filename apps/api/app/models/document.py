"""Knowledge document metadata (PRD §4.8)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.enums import DocumentStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="text/plain", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=DocumentStatus.PENDING.value, index=True, nullable=False
    )
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Retrieval filters (arch §4.7): language, product line, ACL groups, validity window.
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    product: Mapped[str | None] = mapped_column(String(64), nullable=True)
    acl_groups: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
