"""order/models persistent entities (amounts are integer minor units)."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.constants import CURRENCY_SIZE, HASH_SIZE, ID_SIZE, NAME_SIZE
from app.commerce.core.models import MallRecord


class Cart(MallRecord):
    __tablename__ = "carts"
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)


class CartItem(MallRecord):
    __tablename__ = "cart_items"
    __table_args__ = (CheckConstraint("qty > 0", name="cart_items_check_0"), UniqueConstraint("cart_id", "sku_id"),)
    cart_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("carts.id", ondelete="RESTRICT"), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False, index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class CheckoutToken(MallRecord):
    __tablename__ = "checkout_tokens"
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False, unique=True)
    items_hash: Mapped[str] = mapped_column(String(HASH_SIZE), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class Order(MallRecord):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("total_cents >= 0", name="orders_check_0"), CheckConstraint("wallet_cents >= 0 AND wallet_cents <= total_cents", name="orders_check_1"), CheckConstraint("refunded_cents >= 0 AND refund_reserved_cents >= 0", name="orders_check_2"), CheckConstraint("refunded_cents + refund_reserved_cents <= total_cents", name="orders_check_3"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="PENDING_PAYMENT", nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(CURRENCY_SIZE), default="CNY", nullable=False)
    total_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    wallet_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    refunded_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    refund_reserved_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    address_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fulfillment_status: Mapped[str] = mapped_column(String(NAME_SIZE), default="PENDING_PAYMENT", nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)


class OrderItem(MallRecord):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("qty > 0", name="order_items_check_0"), CheckConstraint("price_cents >= 0", name="order_items_check_1"), CheckConstraint("total_cents = price_cents * qty", name="order_items_check_2"),)
    order_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False, index=True)
    title_snapshot: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    price_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)


class OrderHistory(MallRecord):
    __tablename__ = "order_status_history"
    __table_args__ = (UniqueConstraint("order_id", "version"),)
    order_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    from_status: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)
    to_status: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)

