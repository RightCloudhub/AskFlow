"""Immutable payment boundary; order entities never escape their owning module."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, kw_only=True)
class RefundInstruction:
    id: str
    payment_id: str
    amount_cents: int
    wallet_cents: int
    external_cents: int


@dataclass(frozen=True, kw_only=True)
class RefundReceipt:
    provider_ref: str
    status: str


class PaymentGateway(Protocol):
    async def charge(self, db, request): ...

    async def refund(self, db, request: RefundInstruction): ...

    async def query(self, db, request_key: str): ...
