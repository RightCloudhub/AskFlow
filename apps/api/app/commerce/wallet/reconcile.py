"""Detect unbalanced entries, broken hashes and snapshot drift without repairing evidence."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.commerce.core.events import publish
from app.commerce.core.services import enabled
from app.commerce.wallet.journal import chain_head, row_hash
from app.commerce.wallet.models import JournalEntry, Posting, WalletAccount, WalletChainHead
from app.commerce.wallet.operations_models import ReconciliationDiff, ReconciliationRun
from app.core.config import get_settings


async def reconcile(db, *, business_date: str):
    run = ReconciliationRun(business_date=business_date, started_at=datetime.now(UTC))
    db.add(run)
    await db.flush()
    # Hold all currency heads to obtain a stable financial snapshot during this scan.
    await chain_head(db, get_settings().mall_currency)
    heads = list(await db.scalars(select(WalletChainHead).order_by(WalletChainHead.currency).with_for_update()))
    expected, chains = {}, {}
    count = 0
    entries = await db.stream_scalars(select(JournalEntry).order_by(JournalEntry.currency, JournalEntry.seq))
    async for entry in entries:
        count += await _entry(db, run, entry=entry, expected=expected, chains=chains)
    for head in heads:
        if chains.get(head.currency, (0, "")) != (head.seq, head.row_hash):
            count += _diff(db, run, entity=head.id, kind="chain_head", expected={}, actual={})
    accounts = await db.stream_scalars(select(WalletAccount))
    async for account in accounts:
        debit_balance = expected.get(account.id, 0)
        balance = debit_balance if account.normal_side == "debit" else -debit_balance
        if balance != account.balance_cents:
            count += _diff(db, run, entity=account.id, kind="snapshot",
                           expected={"balance": balance}, actual={"balance": account.balance_cents})
    if enabled("payment"):
        from app.commerce.payment.reconciliation import differences

        async for difference in differences(db, business_date=business_date):
            count += _diff(db, run, **difference)
    run.status, run.finished_at, run.summary = "completed", datetime.now(UTC), {"differences": count}
    await publish(db, run, event_type="mall.reconciliation.completed", payload={"run_id": run.id, **run.summary})
    return {"id": run.id, **run.summary}


async def _entry(db, run, *, entry, expected, chains):
    lines = list(await db.scalars(select(Posting).where(Posting.journal_id == entry.id)))
    debit = sum(line.amount_cents for line in lines if line.side == "debit")
    credit = sum(line.amount_cents for line in lines if line.side == "credit")
    count = 0
    if debit != credit or debit != entry.total_cents:
        count += _diff(db, run, entity=entry.id, kind="unbalanced", expected={"debit": debit}, actual={"credit": credit})
    previous_seq, previous_hash = chains.get(entry.currency, (0, ""))
    if (entry.seq, entry.prev_hash) != (previous_seq + 1, previous_hash) or entry.row_hash != row_hash(entry, lines):
        count += _diff(db, run, entity=entry.id, kind="hash_chain", expected={}, actual={})
    chains[entry.currency] = (entry.seq, entry.row_hash)
    accumulate(expected, lines)
    return count


def accumulate(expected, lines):
    for line in lines:
        expected[line.account_id] = expected.get(line.account_id, 0) + (
            line.amount_cents if line.side == "debit" else -line.amount_cents)


def _diff(db, run, *, entity, kind, expected, actual):
    db.add(ReconciliationDiff(run_id=run.id, entity_id=entity, kind=kind,
                              expected=expected, actual=actual))
    return 1
