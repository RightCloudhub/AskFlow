"""Offline conversation reads are scoped, policy checked and recorded."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.commerce.core.errors import MallError
from app.commerce.support.reads import read
from app.models.operation_ledger import OperationLedgerEntry
from .helpers import place, seed, transaction


def context(db, identity, *, assurance=1):
    return SimpleNamespace(db=db, user=SimpleNamespace(id=identity["user_id"]), claims={"assurance": assurance})


@pytest.mark.asyncio
async def test_order_and_wallet_reads_record_gateway_outcomes(mall_runtime):
    identity = await seed(mall_runtime)
    order = await transaction(mall_runtime, lambda db: place(db, identity))
    found = await transaction(mall_runtime, lambda db: read(context(db, identity), "mall.order.get", order_id=order["id"]))
    assert found["status"] == "PENDING_PAYMENT"
    wallet = await transaction(mall_runtime, lambda db: read(context(db, identity), "mall.wallet.balance"))
    assert wallet["available_cents"] == 0
    async with mall_runtime.sessions() as db:
        rows = list(await db.scalars(select(OperationLedgerEntry).where(OperationLedgerEntry.status == "EXECUTED")))
        assert {row.capability for row in rows} == {"mall.order.get", "mall.wallet.balance"}


@pytest.mark.asyncio
async def test_read_cannot_disclose_foreign_order(mall_runtime):
    owner, intruder = await seed(mall_runtime), await seed(mall_runtime)
    order = await transaction(mall_runtime, lambda db: place(db, owner))
    with pytest.raises(MallError, match="resource_not_found") as caught:
        await transaction(mall_runtime, lambda db: read(context(db, intruder), "mall.logistics.get", order_id=order["id"]))
    assert caught.value.status == 404
