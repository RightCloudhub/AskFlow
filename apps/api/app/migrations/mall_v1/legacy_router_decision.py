"""Persisted turn-routing decisions so misroutes can be replayed and evaluated (arch §4.3)."""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.migrations.mall_v1.base import Base
from app.migrations.mall_v1.legacy_mixins import TimestampMixin, UUIDPrimaryKeyMixin

ID_LENGTH = 36
NAME_LENGTH = 128
ROUTE_LENGTH = 32
METHOD_LENGTH = 32
VERSION_LENGTH = 32


class RouterDecisionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "router_decisions"

    turn_id: Mapped[str] = mapped_column(String(ID_LENGTH), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(ID_LENGTH), nullable=False, index=True)
    route: Mapped[str] = mapped_column(String(ROUTE_LENGTH), nullable=False, index=True)
    goal_key: Mapped[str | None] = mapped_column(String(NAME_LENGTH), nullable=True)
    goal_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    method: Mapped[str] = mapped_column(String(METHOD_LENGTH), nullable=False, default="rule")
    slots: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    missing_slots: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    identity_requirement: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    active_task_relation: Mapped[str | None] = mapped_column(String(METHOD_LENGTH), nullable=True)
    router_version: Mapped[str] = mapped_column(String(VERSION_LENGTH), nullable=False, default="1")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
