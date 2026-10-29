"""Cursor-paged finance projections; customer APIs use owner-scoped services."""

from fastapi import APIRouter
from sqlalchemy import select

from app.commerce.admin.permissions import require
from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.schemas import view
from app.commerce.wallet.models import WalletAccount
from app.commerce.wallet.operations_models import WalletAdjustment

WALLET_READ = require("wallet:read")

router = APIRouter()


async def page(db, model, *, cursor: str, fields: tuple):
    rows = list(await db.scalars(select(model).where(model.id > cursor)
        .order_by(model.id).limit(PAGE_SIZE + 1)))
    return {"items": [view(row, fields) for row in rows[:PAGE_SIZE]],
            "next_cursor": rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None}


@router.get("/accounts")
async def accounts(cursor: str = "", ctx=WALLET_READ):
    return await page(ctx.db, WalletAccount, cursor=cursor,
        fields=("id", "user_id", "code", "currency", "balance_cents", "version"))


@router.get("/adjustments")
async def adjustments(cursor: str = "", ctx=WALLET_READ):
    return await page(ctx.db, WalletAdjustment, cursor=cursor,
        fields=("id", "user_id", "amount_cents", "reason", "requested_by", "approved_by",
                "journal_id", "status", "version"))
