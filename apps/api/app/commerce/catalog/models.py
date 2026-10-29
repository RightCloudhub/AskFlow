"""catalog/models persistent entities (amounts are integer minor units)."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.commerce.core.constants import CURRENCY_SIZE, ID_SIZE, NAME_SIZE
from app.commerce.core.models import MallRecord


class Category(MallRecord):
    __tablename__ = "categories"
    parent_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    slug: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Spu(MallRecord):
    __tablename__ = "spus"
    category_id: Mapped[str | None] = mapped_column(String(ID_SIZE), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    images: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="draft", nullable=False, index=True)


class Sku(MallRecord):
    __tablename__ = "skus"
    spu_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("spus.id", ondelete="RESTRICT"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(NAME_SIZE), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(NAME_SIZE), default="draft", nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(CURRENCY_SIZE), default="CNY", nullable=False)


class SkuPrice(MallRecord):
    __tablename__ = "sku_prices"
    __table_args__ = (CheckConstraint("original_cents >= 0", name="sku_prices_check_0"), CheckConstraint("sale_cents >= 0", name="sku_prices_check_1"), CheckConstraint("activity_cents IS NULL OR activity_cents >= 0", name="sku_prices_check_2"),)
    sku_id: Mapped[str] = mapped_column(String(ID_SIZE), ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False, index=True)
    original_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sale_cents: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    activity_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

