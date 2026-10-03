"""Durable dispatch and lease for a service task; no in-memory queue dependency."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ID_LENGTH = 36
ERROR_CODE_LENGTH = 64


class ServiceDispatch(Base):
    __tablename__ = "service_dispatches"

    task_id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    lease_token: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notified_version: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    last_error: Mapped[str | None] = mapped_column(String(ERROR_CODE_LENGTH), nullable=True)
