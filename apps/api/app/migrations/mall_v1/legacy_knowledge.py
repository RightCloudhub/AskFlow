"""Knowledge gap and draft models (PRD §4.9)."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.migrations.mall_v1.base import Base
from app.migrations.mall_v1.legacy_enums import DraftStatus, GapStatus
from app.migrations.mall_v1.legacy_mixins import TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeGap(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "knowledge_gaps"

    question: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_question: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=GapStatus.OPEN.value, index=True, nullable=False
    )
    hit_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(128), nullable=True)


class KnowledgeDraft(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "knowledge_drafts"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(32), default=DraftStatus.DRAFT.value, index=True, nullable=False
    )
    gap_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
