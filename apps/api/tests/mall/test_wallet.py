"""Concurrent balance correctness, immutable evidence and independent reconciliation."""

import asyncio
from datetime import date

import pytest
from sqlalchemy import select, update

from app.commerce.core.errors import MallError
from app.commerce.wallet.journal import Line, balanced
from app.commerce.wallet.models import Posting, WalletAccount
from app.commerce.wallet.reconcile import reconcile
from app.commerce.wallet.service import WalletService
from .helpers import seed, transaction


@pytest.mark.parametrize("lines", [[], [Line("a", "debit", 100)],
    [Line("a", "debit", 0), Line("b", "credit", 0)],
    [Line("a", "debit", True), Line("b", "credit", True)]])
def test_invalid_journal(lines):
    with pytest.raises(MallError):
        balanced(lines)


@pytest.mark.asyncio
async def test_two_hundred_concurrent_movements_balance(mall_runtime):
    identity = await seed(mall_runtime)
    user = identity["user_id"]
    await transaction(mall_runtime, lambda db: WalletService(db).credit(user, 10000, key="initial"))

    async def movement(index):
        debit, credit = ("gateway", "available") if index % 2 else ("available", "sales")
        return await transaction(mall_runtime, lambda db: WalletService(db).transfer(user, amount=10,
            key="movement:" + str(index), debit=debit, credit=credit))

    await asyncio.gather(*(movement(index) for index in range(200)))
    async with mall_runtime.sessions() as db:
        assert (await WalletService(db).balance(user))["available_cents"] == 10000
        report = await reconcile(db, business_date=date.today().isoformat())
        assert report["differences"] == 0


@pytest.mark.asyncio
async def test_insufficient_balance_rolls_back_all_postings(mall_runtime):
    identity = await seed(mall_runtime)
    with pytest.raises(MallError, match="wallet_insufficient"):
        await transaction(mall_runtime, lambda db: WalletService(db).freeze(identity["user_id"], 1, key="overdraw"))
    async with mall_runtime.sessions() as db:
        assert list(await db.scalars(select(Posting))) == []


@pytest.mark.asyncio
async def test_snapshot_tamper_is_detected(mall_runtime):
    identity = await seed(mall_runtime)
    await transaction(mall_runtime, lambda db: WalletService(db).credit(identity["user_id"], 100, key="fund"))
    async with mall_runtime.sessions() as db:
        await db.execute(update(WalletAccount).where(WalletAccount.user_id == identity["user_id"])
                         .values(balance_cents=999))
        await db.commit()
    report = await transaction(mall_runtime, lambda db: reconcile(db, business_date=date.today().isoformat()))
    assert report["differences"] > 0
