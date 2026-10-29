"""Checkout carries item identity/quantity, never authoritative totals."""

from typing import Literal

from pydantic import Field

from app.commerce.core.constants import NAME_SIZE
from app.commerce.core.schemas import PositiveCents, Schema, Versioned

MAX_ITEMS = 50
MAX_QUANTITY = 100


class Item(Schema):
    sku_id: str
    qty: int = Field(strict=True, gt=0, le=MAX_QUANTITY)


class Checkout(Schema):
    items: list[Item] = Field(min_length=1, max_length=MAX_ITEMS)
    address_id: str | None = None


class PlaceOrder(Checkout):
    checkout_token: str


class Change(Versioned):
    confirmation_token: str = ""
    reason: str = Field(default="customer_request", max_length=NAME_SIZE)


class Transition(Versioned):
    status: Literal["SHIPPED", "DELIVERED", "COMPLETED"]
    tracking_number: str = Field(default="", max_length=NAME_SIZE)


class RefundRequest(Schema):
    amount_cents: PositiveCents
    reason: str = Field(min_length=1, max_length=NAME_SIZE)
    destination: Literal["original", "wallet"] = "original"
    confirmation_token: str = ""
