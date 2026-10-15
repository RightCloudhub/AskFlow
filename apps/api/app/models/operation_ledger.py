"""Append-only operation ledger: every governed action from both execution modes (arch §4.11)."""

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin

ID_LENGTH = 36
NAME_LENGTH = 128
KEY_LENGTH = 128
HASH_LENGTH = 64
STATUS_LENGTH = 32
ACTOR_LENGTH = 32
REF_LENGTH = 255


class OperationLedgerEntry(Base, TimestampMixin):
    """Immutable rows; a status change is a new row with the same idempotency key."""

    __tablename__ = "operation_ledger"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    op_id: Mapped[str] = mapped_column(String(ID_LENGTH), nullable=False, unique=True, index=True)
    organization_id: Mapped[str] = mapped_column(String(NAME_LENGTH), index=True)
    customer_id: Mapped[str] = mapped_column(String(NAME_LENGTH), index=True)
    task_id: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True, index=True)
    turn_id: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True, index=True)
    step: Mapped[str | None] = mapped_column(String(NAME_LENGTH), nullable=True)
    capability: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    capability_version: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False, default="1")
    args_hash: Mapped[str] = mapped_column(String(HASH_LENGTH), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(KEY_LENGTH), nullable=False, index=True)
    policy_decision: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    policy_version: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    actor: Mapped[str] = mapped_column(String(ACTOR_LENGTH), nullable=False, default="agent")
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(REF_LENGTH), nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(HASH_LENGTH), nullable=True)
    row_hash: Mapped[str] = mapped_column(String(HASH_LENGTH), nullable=False)
