"""Strict gateway envelopes use integer cents and bounded identifiers."""

from typing import Literal

from pydantic import Field

from app.commerce.core.constants import NAME_SIZE
from app.commerce.core.schemas import Cents, Schema


class StartPayment(Schema):
    order_id: str
    method: Literal["mock", "wallet", "mixed"] = "mock"
    wallet_cents: Cents = 0
    step_up_token: str = ""


class Callback(Schema):
    payment_id: str
    transaction_id: str = Field(min_length=1, max_length=NAME_SIZE)
    amount_cents: Cents
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    status: Literal["succeeded", "failed"]
    timestamp: int = Field(strict=True, gt=0)


class MockOutcome(Schema):
    status: Literal["succeeded", "failed"] = "succeeded"
    deliver_callback: bool = True
