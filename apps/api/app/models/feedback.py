"""Message feedback thumbs (PRD §4.5)."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Feedback(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "feedbacks"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),)

    message_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    # 1=up, -1=down, 0=neutral
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
