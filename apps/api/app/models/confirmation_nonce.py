"""Single-use nonces backing signed confirmation tokens (arch §15.3)."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

ID_LENGTH = 36
NONCE_LENGTH = 64
HASH_LENGTH = 64
STEP_LENGTH = 128


class ConfirmationNonce(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "confirmation_nonces"

    nonce: Mapped[str] = mapped_column(String(NONCE_LENGTH), nullable=False, unique=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True, index=True)
    turn_id: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True)
    step: Mapped[str] = mapped_column(String(STEP_LENGTH), nullable=False, default="")
    args_hash: Mapped[str] = mapped_column(String(HASH_LENGTH), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
