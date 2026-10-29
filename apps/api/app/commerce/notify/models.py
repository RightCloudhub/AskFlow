"""notify/models persistent entities (amounts are integer minor units)."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.constants import ID_SIZE, NAME_SIZE
from app.commerce.core.models import MallRecord


class NotificationTemplate(MallRecord):
    __tablename__ = "notification_templates"
    __table_args__ = (UniqueConstraint("event_type", "locale", "version"),)
    event_type: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    locale: Mapped[str] = mapped_column(String(NAME_SIZE), default="zh-CN", nullable=False)
    subject: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    channels: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Notification(MallRecord):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "event_id"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(ID_SIZE), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    locale: Mapped[str] = mapped_column(String(NAME_SIZE), default="zh-CN", nullable=False)
    subject: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class NotificationDelivery(MallRecord):
    __tablename__ = "notification_deliveries"
    __table_args__ = (UniqueConstraint("notification_id", "channel"),)
    notification_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("notifications.id", ondelete="RESTRICT"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="pending", nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_error: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    provider_ref: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)


class NotificationPreference(MallRecord):
    __tablename__ = "user_notification_prefs"
    __table_args__ = (UniqueConstraint("user_id", "event_type", "channel"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    channel: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_start: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)
    quiet_end: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)
    timezone: Mapped[str] = mapped_column(String(NAME_SIZE), default="UTC", nullable=False)

