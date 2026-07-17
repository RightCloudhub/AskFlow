"""Conversation and Message models (PRD §4.5 / §6)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.enums import ConversationStatus, MessageRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

JSONType = JSON().with_variant(SQLITE_JSON(), "sqlite")


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="新会话", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=ConversationStatus.ACTIVE.value, index=True, nullable=False
    )
    # merge-patch only (PRD §6.3)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin",
    )


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=MessageRole.USER.value)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # intent, route, sources, confidence, run_id, etc.
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
