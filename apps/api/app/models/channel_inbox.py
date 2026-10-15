"""Deduplicated inbound channel messages; replay-safe webhook ingestion (arch §9.1)."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

NAME_LENGTH = 128
MESSAGE_ID_LENGTH = 255
SESSION_KEY_LENGTH = 255
ERROR_LENGTH = 255


class ChannelInbox(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "channel_inbox"
    __table_args__ = (
        UniqueConstraint("channel", "channel_message_id", name="uq_channel_inbox_message"),
    )

    channel: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False, index=True)
    channel_message_id: Mapped[str] = mapped_column(String(MESSAGE_ID_LENGTH), nullable=False)
    session_key: Mapped[str] = mapped_column(String(SESSION_KEY_LENGTH), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    lease_token: Mapped[str | None] = mapped_column(String(MESSAGE_ID_LENGTH), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(ERROR_LENGTH), nullable=True)
