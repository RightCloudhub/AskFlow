"""Prompt template versioning (PRD §4.10)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PromptTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "prompt_templates"

    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    active_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    versions = relationship(
        "PromptVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PromptVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("template_id", "version", name="uq_prompt_version"),)

    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("prompt_templates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    template = relationship("PromptTemplate", back_populates="versions")
