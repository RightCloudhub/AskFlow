"""Leased business-object ownership across independently dispatched tasks."""

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin

SCOPE_LENGTH = 128
OBJECT_KEY_LENGTH = 255
TASK_ID_LENGTH = 36


class ServiceObjectLock(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "service_object_locks"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "customer_id", "object_key", name="uq_service_object_lock_scope_key"
        ),
    )

    organization_id: Mapped[str] = mapped_column(String(SCOPE_LENGTH), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(SCOPE_LENGTH), nullable=False)
    object_key: Mapped[str] = mapped_column(String(OBJECT_KEY_LENGTH), nullable=False)
    task_id: Mapped[str] = mapped_column(String(TASK_ID_LENGTH), nullable=False)
    lease_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
