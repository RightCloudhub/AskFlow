"""Commerce-wide durable coordination, idempotency and consumer receipts."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.constants import HASH_SIZE, ID_SIZE, NAME_SIZE
from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MallRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __abstract__ = True
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class IdempotencyRecord(MallRecord):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("scope", "key_hash"),)
    scope: Mapped[str] = mapped_column(String(NAME_SIZE))
    key_hash: Mapped[str] = mapped_column(String(HASH_SIZE))
    request_hash: Mapped[str] = mapped_column(String(HASH_SIZE))
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="pending")
    response: Mapped[dict | None] = mapped_column(JSON)
    http_status: Mapped[int | None] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WorkerLease(MallRecord):
    __tablename__ = "worker_leases"
    key: Mapped[str] = mapped_column(String(NAME_SIZE), unique=True)
    owner: Mapped[str] = mapped_column(String(ID_SIZE))
    fence: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class EventConsumerReceipt(Base):
    __tablename__ = "event_consumer_receipts"
    event_id: Mapped[str] = mapped_column(String(ID_SIZE), primary_key=True)
    consumer: Mapped[str] = mapped_column(String(NAME_SIZE), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
