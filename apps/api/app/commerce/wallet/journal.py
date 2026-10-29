"""Balanced immutable entries; a currency chain head serializes all appenders."""

from dataclasses import dataclass
from http import HTTPStatus
from typing import Literal

from sqlalchemy import select

from app.commerce.core.constants import MAX_SAFE_CENTS
from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.repository import cas, insert_once
from app.commerce.wallet.models import JournalEntry, Posting, WalletAccount, WalletChainHead
from app.services.agent.gateway.idempotency import args_hash


@dataclass(frozen=True)
class Line:
    account_id: str
    side: Literal["debit", "credit"]
    amount_cents: int


@dataclass(frozen=True, kw_only=True)
class Journal:
    business_key: str
    currency: str
    lines: tuple[Line, ...]
    description: str = ""
    actor_id: str | None = None
    reversal_of: str | None = None


def balanced(lines) -> int:
    if not lines or any(invalid_line(line) for line in lines):
        raise MallError("invalid_postings", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    debit = sum(line.amount_cents for line in lines if line.side == "debit")
    credit = sum(line.amount_cents for line in lines if line.side == "credit")
    if debit != credit:
        raise MallError("journal_unbalanced", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    return debit


def invalid_line(line):
    return (type(line.amount_cents) is not int or line.amount_cents <= 0
            or line.side not in {"debit", "credit"})


def material(row, lines):
    return {"business_key": row.business_key, "currency": row.currency,
            "description": row.description, "actor_id": row.actor_id,
            "reversal_of": row.reversal_of,
            "lines": sorted([(line.account_id, line.side, line.amount_cents) for line in lines])}


def row_hash(row, lines):
    return args_hash({**material(row, lines), "seq": row.seq, "prev_hash": row.prev_hash})


async def chain_head(db, currency: str):
    await insert_once(db, WalletChainHead, values={"currency": currency}, unique=["currency"])
    return await db.scalar(select(WalletChainHead).where(WalletChainHead.currency == currency)
        .with_for_update().execution_options(populate_existing=True))


async def append(db, request: Journal):
    total = balanced(request.lines)
    head = await chain_head(db, request.currency)
    prior = await db.scalar(select(JournalEntry).where(JournalEntry.business_key == request.business_key))
    if prior:
        lines = list(await db.scalars(select(Posting).where(Posting.journal_id == prior.id)))
        if material(prior, lines) != material(request, request.lines):
            raise MallError("journal_idempotency_conflict")
        return prior
    accounts = await lock_accounts(db, request)
    for account in accounts:
        await update_balance(db, account, request)
    row = JournalEntry(business_key=request.business_key, currency=request.currency,
        description=request.description, actor_id=request.actor_id, reversal_of=request.reversal_of,
        total_cents=total, seq=head.seq + 1, prev_hash=head.row_hash, row_hash="")
    row.row_hash = row_hash(row, request.lines)
    db.add(row)
    await db.flush()
    db.add_all([Posting(journal_id=row.id, account_id=line.account_id, side=line.side,
                        amount_cents=line.amount_cents) for line in request.lines])
    await cas(db, head, values={"seq": row.seq, "row_hash": row.row_hash})
    await publish(db, row, event_type="mall.wallet.posted", payload={
        "journal_id": row.id, "user_id": request.actor_id, "currency": request.currency})
    await db.flush()
    return row


async def lock_accounts(db, request):
    keys = {line.account_id for line in request.lines}
    rows = list(await db.scalars(select(WalletAccount).where(WalletAccount.id.in_(keys))
        .order_by(WalletAccount.code).with_for_update().execution_options(populate_existing=True)))
    if len(rows) != len(keys) or any(row.currency != request.currency for row in rows):
        raise MallError("journal_account_mismatch")
    return rows


async def update_balance(db, account, request):
    delta = sum(line.amount_cents if line.side == account.normal_side else -line.amount_cents
                for line in request.lines if line.account_id == account.id)
    balance = account.balance_cents + delta
    if abs(balance) > MAX_SAFE_CENTS:
        raise MallError("wallet_balance_limit")
    if not account.allow_negative and balance < 0:
        raise MallError("wallet_insufficient")
    await cas(db, account, values={"balance_cents": balance})


async def reverse(db, journal_id: str, *, business_key: str, actor_id: str):
    row = await db.get(JournalEntry, journal_id)
    if row is None:
        raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
    await chain_head(db, row.currency)
    prior = await db.scalar(select(JournalEntry).where(JournalEntry.reversal_of == row.id))
    if prior is not None:
        if prior.business_key == business_key:
            return prior
        raise MallError("journal_already_reversed")
    lines = await db.scalars(select(Posting).where(Posting.journal_id == row.id))
    opposite = {"debit": "credit", "credit": "debit"}
    request = Journal(business_key=business_key, currency=row.currency, actor_id=actor_id,
        reversal_of=row.id, description="reversal", lines=tuple(
            Line(line.account_id, opposite[line.side], line.amount_cents) for line in lines))
    return await append(db, request)
