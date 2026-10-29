"""order/refund_models persistent entities (amounts are integer minor units)."""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.constants import ID_SIZE, NAME_SIZE
from app.commerce.core.models import MallRecord


class Refund(MallRecord):
    __tablename__ = "refunds"
    __table_args__ = (CheckConstraint("amount_cents > 0", name="refunds_check_0"), CheckConstraint("wallet_cents >= 0 AND external_cents >= 0", name="refunds_check_1"), CheckConstraint("wallet_cents + external_cents = amount_cents", name="refunds_check_2"),)
    order_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    payment_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=True, index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    wallet_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    external_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="requested", nullable=False, index=True)
    request_key: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    approval_actor: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    provider_ref: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    reason: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    original_status: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    destination: Mapped[str] = mapped_column(String(NAME_SIZE), default="original", nullable=False)

