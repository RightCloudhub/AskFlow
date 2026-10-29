"""Two-person correction, immutable findings and once-daily reconciliation."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select, update

from app.commerce.core.errors import MallError
from app.commerce.wallet.corrections import approve_reversal, request_reversal, resolve_difference
from app.commerce.wallet.journal import reverse
from app.commerce.wallet.models import JournalEntry, WalletAccount
from app.commerce.wallet.operations_models import ReconciliationDiff, ReconciliationRun
from app.commerce.wallet.schedule import daily
from app.commerce.wallet.service import WalletService

from .helpers import seed, transaction


def context(db, identity):
    return SimpleNamespace(db=db, user=SimpleNamespace(id=identity["user_id"]))


@pytest.mark.asyncio
async def test_reversal_requires_independent_operator_and_reverses_once(mall_runtime):
    customer = await seed(mall_runtime)
    first, second = await seed(mall_runtime), await seed(mall_runtime)
    credit = await transaction(mall_runtime, lambda db: WalletService(db).credit(
        customer["user_id"], 100, key="original"))
    request = await transaction(mall_runtime, lambda db: request_reversal(context(db, first),
        SimpleNamespace(journal_id=credit["id"], reason="incorrect credit")))
    payload = SimpleNamespace(approved=True, expected_version=request["version"])
    with pytest.raises(MallError, match="dual_control_required"):
        await transaction(mall_runtime, lambda db: approve_reversal(context(db, first), request["id"], payload))
    approved = await transaction(mall_runtime, lambda db: approve_reversal(context(db, second), request["id"], payload))
    assert approved["status"] == "approved"
    async with mall_runtime.sessions() as db:
        assert (await WalletService(db).balance(customer["user_id"]))["available_cents"] == 0
        rows = list(await db.scalars(select(JournalEntry).order_by(JournalEntry.seq)))
        assert len(rows) == 2 and rows[1].reversal_of == rows[0].id
    with pytest.raises(MallError, match="journal_already_reversed"):
        await transaction(mall_runtime, lambda db: reverse(db, credit["id"],
            business_key="second-reversal", actor_id=second["user_id"]))


@pytest.mark.asyncio
async def test_daily_lease_reuses_completed_result(mall_runtime):
    first = await transaction(mall_runtime, daily)
    second = await transaction(mall_runtime, daily)
    assert first["id"] == second["id"]
    async with mall_runtime.sessions() as db:
        assert len(list(await db.scalars(select(ReconciliationRun)))) == 1


@pytest.mark.asyncio
async def test_review_keeps_original_difference_evidence(mall_runtime):
    customer = await seed(mall_runtime)
    await transaction(mall_runtime, lambda db: WalletService(db).credit(customer["user_id"], 100, key="fund"))

    async def tamper(db):
        await db.execute(update(WalletAccount).where(WalletAccount.user_id == customer["user_id"])
                         .values(balance_cents=999))

    await transaction(mall_runtime, tamper)
    await transaction(mall_runtime, daily)
    async with mall_runtime.sessions() as db:
        row = await db.scalar(select(ReconciliationDiff).where(ReconciliationDiff.kind == "snapshot"))
        identifier, expected, actual, version = row.id, row.expected, row.actual, row.version
    payload = SimpleNamespace(expected_version=version, reference="case-123", reason="investigated")
    result = await transaction(mall_runtime, lambda db: resolve_difference(context(db, customer), identifier, payload))
    assert result["status"] == "reviewed"
    async with mall_runtime.sessions() as db:
        row = await db.get(ReconciliationDiff, identifier)
        assert row.expected == expected and row.actual == actual
        assert (await WalletService(db).balance(customer["user_id"]))["available_cents"] == 999
