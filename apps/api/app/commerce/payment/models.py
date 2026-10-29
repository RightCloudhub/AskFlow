"""payment/models persistent entities (amounts are integer minor units)."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.constants import CURRENCY_SIZE, HASH_SIZE, ID_SIZE, NAME_SIZE
from app.commerce.core.models import MallRecord


class Payment(MallRecord):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount_cents >= 0", name="payments_check_0"), CheckConstraint("wallet_cents >= 0 AND external_cents >= 0", name="payments_check_1"), CheckConstraint("wallet_cents + external_cents = amount_cents", name="payments_check_2"), CheckConstraint("refunded_cents >= 0 AND refunded_cents <= amount_cents", name="payments_check_3"),)
    order_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=True, unique=True)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    topup_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("topups.id", ondelete="RESTRICT"), nullable=True, unique=True)
    method: Mapped[str] = mapped_column(String(NAME_SIZE), default="mock", nullable=False)
    currency: Mapped[str] = mapped_column(String(CURRENCY_SIZE), default="CNY", nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    wallet_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    external_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    refunded_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="created", nullable=False, index=True)
    request_key: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    provider_ref: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    payer_hash: Mapped[str] = mapped_column(String(HASH_SIZE), default="", nullable=False, index=True)


class PaymentCallback(MallRecord):
    __tablename__ = "payment_callbacks"
    __table_args__ = (UniqueConstraint("channel", "transaction_id"),)
    channel: Mapped[str] = mapped_column(String(NAME_SIZE), default="mock", nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True)
    body_digest: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="pending", nullable=False)
    error_kind: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)


class GatewayTransaction(MallRecord):
    __tablename__ = "gateway_transactions"
    request_key: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    payment_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=True, index=True)
    refund_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("refunds.id", ondelete="RESTRICT"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(NAME_SIZE), default="charge", nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(CURRENCY_SIZE), default="CNY", nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="pending", nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    payer_hash: Mapped[str] = mapped_column(String(HASH_SIZE), default="", nullable=False)

