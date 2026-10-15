"""Step-up verification challenges for sensitive goals (arch §4.2 / §9.3)."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

ID_LENGTH = 36
NAME_LENGTH = 128
HASH_LENGTH = 64
PURPOSE_LENGTH = 64


class OtpChallenge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "otp_challenges"

    user_id: Mapped[str] = mapped_column(String(ID_LENGTH), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    purpose: Mapped[str] = mapped_column(String(PURPOSE_LENGTH), nullable=False, default="step_up")
    code_hash: Mapped[str] = mapped_column(String(HASH_LENGTH), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
