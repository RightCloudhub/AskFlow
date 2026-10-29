"""wallet/operations_models persistent entities (amounts are integer minor units)."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.migrations.mall_v1.constants import CURRENCY_SIZE, ID_SIZE, NAME_SIZE
from app.migrations.mall_v1.core_models import MallRecord


class Topup(MallRecord):
    __tablename__ = "topups"
    __table_args__ = (CheckConstraint("amount_cents > 0", name="topups_check_0"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    payment_id: Mapped[str | None] = mapped_column(String(ID_SIZE), nullable=True, index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(CURRENCY_SIZE), nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="created", nullable=False, index=True)
    request_key: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)


class WalletAdjustment(MallRecord):
    __tablename__ = "wallet_adjustments"
    __table_args__ = (CheckConstraint("amount_cents != 0", name="wallet_adjustments_check_0"), CheckConstraint("approved_by IS NULL OR approved_by != requested_by", name="wallet_adjustments_check_1"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    approved_by: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="pending", nullable=False)
    journal_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("wallet_journal_entries.id", ondelete="RESTRICT"), nullable=True, index=True)


class ReconciliationRun(MallRecord):
    __tablename__ = "reconciliation_runs"
    business_date: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    kind: Mapped[str] = mapped_column(String(NAME_SIZE), default="daily", nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="running", nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class ReconciliationDiff(MallRecord):
    __tablename__ = "reconciliation_diffs"
    __table_args__ = (UniqueConstraint("run_id", "entity_id", "kind"),)
    run_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("reconciliation_runs.id", ondelete="RESTRICT"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    kind: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    severity: Mapped[str] = mapped_column(String(NAME_SIZE), default="critical", nullable=False)
    expected: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    actual: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="open", nullable=False)
    resolution_ref: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
