"""Versioned customer-service checkpoints, scoped independently of conversations."""

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

SCOPE_LENGTH = 128


class ServiceTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "service_tasks"

    organization_id: Mapped[str] = mapped_column(String(SCOPE_LENGTH), index=True)
    customer_id: Mapped[str] = mapped_column(String(SCOPE_LENGTH), index=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    checkpoint: Mapped[dict] = mapped_column(JSON, nullable=False)
