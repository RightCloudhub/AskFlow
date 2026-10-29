"""All wallet movement is expressed as balanced postings, including freezes."""

from sqlalchemy import func, select

from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.repository import insert_once
from app.commerce.core.schemas import view
from app.commerce.wallet.journal import Journal, Line, append, reverse
from app.commerce.wallet.models import JournalEntry, Posting, WalletAccount
from app.core.config import get_settings

USER_KINDS = frozenset({"available", "frozen"})
DEBIT_KINDS = frozenset({"gateway", "marketing", "adjustment"})
ENTRY_FIELDS = ("id", "business_key", "currency", "description", "total_cents", "created_at", "row_hash")


class WalletService:
    def __init__(self, db):
        self.db = db

    async def account(self, kind: str, *, user_id: str | None = None):
        currency = get_settings().mall_currency
        code = currency + ":" + kind + ":" + (user_id or "platform")
        await insert_once(self.db, WalletAccount, values={"code": code, "user_id": user_id,
            "currency": currency, "normal_side": "debit" if kind in DEBIT_KINDS else "credit",
            "allow_negative": kind not in USER_KINDS}, unique=["code"])
        return await self.db.scalar(select(WalletAccount).where(WalletAccount.code == code))

    async def lock(self):
        from app.commerce.wallet.journal import chain_head

        await chain_head(self.db, get_settings().mall_currency)

    async def balance(self, user_id: str):
        rows = await self.db.scalars(select(WalletAccount).where(WalletAccount.user_id == user_id))
        values = {row.code.split(":")[1]: row.balance_cents for row in rows}
        return {"currency": get_settings().mall_currency, "available_cents": values.get("available", 0),
                "frozen_cents": values.get("frozen", 0)}

    async def transfer(self, user_id: str, *, amount: int, key: str, debit: str, credit: str):
        if not amount:
            return None
        # The chain lock precedes account creation as well as account row locks.
        from app.commerce.wallet.journal import chain_head

        await chain_head(self.db, get_settings().mall_currency)
        from app.commerce.account.repository import identity_by_id

        if await identity_by_id(self.db, user_id) is None:
            raise MallError("account_inactive")
        debit_account = await self.account(debit, user_id=user_id if debit in USER_KINDS else None)
        credit_account = await self.account(credit, user_id=user_id if credit in USER_KINDS else None)
        row = await append(self.db, Journal(business_key=key, currency=get_settings().mall_currency,
            description=key.split(":")[0], actor_id=user_id,
            lines=(Line(debit_account.id, "debit", amount), Line(credit_account.id, "credit", amount))))
        return {"id": row.id, "business_key": row.business_key}

    async def freeze(self, user_id: str, amount: int, *, key: str):
        return await self.transfer(user_id, amount=amount, key=key, debit="available", credit="frozen")

    async def unfreeze(self, user_id: str, amount: int, *, key: str):
        return await self.transfer(user_id, amount=amount, key=key, debit="frozen", credit="available")

    async def settle(self, user_id: str, *, wallet: int, external: int, key: str):
        await self.transfer(user_id, amount=wallet, key=key + ":wallet", debit="frozen", credit="sales")
        await self.transfer(user_id, amount=external, key=key + ":gateway", debit="gateway", credit="sales")

    async def credit(self, user_id: str, amount: int, *, key: str, source: str = "gateway"):
        return await self.transfer(user_id, amount=amount, key=key, debit=source, credit="available")

    async def refund(self, user_id: str, *, wallet: int, external: int, key: str):
        await self.transfer(user_id, amount=wallet, key=key + ":wallet", debit="sales", credit="available")
        await self.transfer(user_id, amount=external, key=key + ":gateway", debit="sales", credit="gateway")

    async def reverse(self, journal_id: str, *, key: str, actor_id: str):
        row = await reverse(self.db, journal_id, business_key=key, actor_id=actor_id)
        return {"id": row.id}

    async def entries(self, user_id: str, *, cursor: str = ""):
        statement = select(JournalEntry).join(Posting, Posting.journal_id == JournalEntry.id)
        statement = statement.join(WalletAccount, WalletAccount.id == Posting.account_id).where(
            WalletAccount.user_id == user_id, JournalEntry.id > cursor).distinct().order_by(JournalEntry.id)
        rows = list(await self.db.scalars(statement.limit(PAGE_SIZE + 1)))
        return {"items": [view(row, ENTRY_FIELDS) for row in rows[:PAGE_SIZE]],
                "next_cursor": rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None}

    async def entry(self, user_id: str, journal_id: str):
        statement = select(JournalEntry).join(Posting, Posting.journal_id == JournalEntry.id).join(
            WalletAccount, WalletAccount.id == Posting.account_id).where(
                WalletAccount.user_id == user_id, JournalEntry.id == journal_id)
        row = await self.db.scalar(statement)
        if row is None:
            raise MallError("resource_not_found", status=404)
        return view(row, ENTRY_FIELDS)

    async def export(self, user_id: str):
        entries, cursor = [], ""
        while True:
            page = await self.entries(user_id, cursor=cursor)
            entries.extend(page["items"])
            if not page["next_cursor"]:
                break
            cursor = page["next_cursor"]
        return {"balance": await self.balance(user_id), "ledger": entries}

    async def total_liability(self):
        return await self.db.scalar(select(func.coalesce(func.sum(WalletAccount.balance_cents), 0))
            .where(WalletAccount.user_id.is_not(None)))
