"""inventory/models persistent entities (amounts are integer minor units)."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.constants import ID_SIZE, NAME_SIZE
from app.commerce.core.models import MallRecord


class Inventory(MallRecord):
    __tablename__ = "inventory"
    __table_args__ = (CheckConstraint("available >= 0", name="inventory_check_0"), CheckConstraint("reserved >= 0", name="inventory_check_1"), CheckConstraint("sold >= 0", name="inventory_check_2"),)
    sku_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    available: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_fence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class InventoryReservation(MallRecord):
    __tablename__ = "inventory_reservations"
    __table_args__ = (CheckConstraint("qty > 0", name="inventory_reservations_check_0"), UniqueConstraint("order_id", "sku_id"),)
    order_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False, index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="reserved", nullable=False, index=True)


class InventoryMovement(MallRecord):
    __tablename__ = "inventory_movements"
    sku_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=True, index=True)
    business_key: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    available_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kind: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)


class FlashSale(MallRecord):
    __tablename__ = "flash_sales"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="flash_sales_check_0"),)
    name: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="active", nullable=False, index=True)


class FlashSaleSku(MallRecord):
    __tablename__ = "flash_sale_skus"
    __table_args__ = (CheckConstraint("stock >= 0", name="flash_sale_skus_check_0"), CheckConstraint("price_cents >= 0", name="flash_sale_skus_check_1"), CheckConstraint("per_user_limit > 0", name="flash_sale_skus_check_2"), UniqueConstraint("sale_id", "sku_id"),)
    sale_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("flash_sales.id", ondelete="RESTRICT"), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False, index=True)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class FlashRequest(MallRecord):
    __tablename__ = "flash_sale_requests"
    __table_args__ = (UniqueConstraint("user_id", "sale_id", "sku_id"),)
    user_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    sale_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("flash_sales.id", ondelete="RESTRICT"), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False, index=True)
    request_key: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="queued", nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    error_code: Mapped[str] = mapped_column(String(NAME_SIZE), default="", nullable=False)

