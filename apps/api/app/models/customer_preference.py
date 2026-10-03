"""Scoped, versioned customer-confirmed preferences; deletions retain no value."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin

SCOPE_LENGTH = 128
PREFERENCE_LENGTH = 32


class CustomerPreference(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "customer_preferences"
    __table_args__ = (UniqueConstraint("organization_id", "customer_id", "key",
                                      name="uq_customer_preference_scope_key"),)

    organization_id: Mapped[str] = mapped_column(String(SCOPE_LENGTH), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(SCOPE_LENGTH), nullable=False)
    key: Mapped[str] = mapped_column(String(PREFERENCE_LENGTH), nullable=False)
    value: Mapped[str | None] = mapped_column(String(PREFERENCE_LENGTH), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
