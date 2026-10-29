"""Dual-control adjustments and reconciliation preserve original evidence."""

from datetime import UTC, date, datetime
from http import HTTPStatus

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select

from app.commerce.account.mfa import require_step_up
from app.commerce.admin.permissions import require
from app.commerce.core.commands import command
from app.commerce.core.constants import MAX_SAFE_CENTS, NAME_SIZE, PAGE_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas
from app.commerce.core.schemas import Schema, Versioned, view
from app.commerce.wallet.corrections_api import router as corrections_router
from app.commerce.wallet.operations_models import (
    ReconciliationDiff,
    ReconciliationRun,
    WalletAdjustment,
)
from app.commerce.wallet.reconcile import reconcile
from app.commerce.wallet.service import WalletService
from app.commerce.wallet.views_api import page
from app.commerce.wallet.views_api import router as views_router

FINANCE_RECONCILE = require("finance:reconcile")
WALLET_ADJUST = require("wallet:adjust")
WALLET_APPROVE = require("wallet:approve")
WALLET_READ = require("wallet:read")

router = APIRouter()
router.include_router(corrections_router)
router.include_router(views_router)


class AdjustmentInput(Schema):
    user_id: str
    amount_cents: int = Field(strict=True, ge=-MAX_SAFE_CENTS, le=MAX_SAFE_CENTS)
    reason: str = Field(min_length=1, max_length=NAME_SIZE)
    step_up_token: str


class Approval(Versioned):
    approved: bool
    step_up_token: str


class ReconcileInput(Schema):
    business_date: date | None = None


@router.get("/{user_id}/balance")
async def balance(user_id: str, ctx=WALLET_READ):
    return await WalletService(ctx.db).balance(user_id)


@router.post("/adjustments")
async def adjustment(payload: AdjustmentInput, ctx=WALLET_ADJUST):
    require_step_up(ctx, payload.step_up_token, purpose="wallet_adjust")
    if not payload.amount_cents:
        raise MallError("invalid_amount", status=HTTPStatus.UNPROCESSABLE_ENTITY)

    async def perform():
        row = WalletAdjustment(user_id=payload.user_id, amount_cents=payload.amount_cents,
            reason=payload.reason, requested_by=ctx.user.id)
        ctx.db.add(row)
        await ctx.db.flush()
        return {"id": row.id, "status": row.status, "version": row.version}

    return await command(ctx, "wallet.adjustment", payload=payload, action=perform)


@router.post("/adjustments/{adjustment_id}/approve")
async def approve(adjustment_id: str, payload: Approval, ctx=WALLET_APPROVE):
    require_step_up(ctx, payload.step_up_token, purpose="wallet_approve")

    async def perform():
        row = await ctx.db.scalar(select(WalletAdjustment).where(WalletAdjustment.id == adjustment_id)
                                  .with_for_update().execution_options(populate_existing=True))
        if row is None:
            raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
        if row.requested_by == ctx.user.id or row.status != "pending" or row.version != payload.expected_version:
            raise MallError("adjustment_approval_conflict")
        journal = None
        if payload.approved:
            journal = await WalletService(ctx.db).transfer(row.user_id, amount=abs(row.amount_cents),
                key="adjustment:" + row.id, debit="adjustment" if row.amount_cents > 0 else "available",
                credit="available" if row.amount_cents > 0 else "adjustment")
        await cas(ctx.db, row, values={"status": "approved" if payload.approved else "rejected",
            "approved_by": ctx.user.id, "journal_id": journal["id"] if journal else None})
        return {"id": row.id, "status": row.status, "journal_id": row.journal_id}

    return await command(ctx, "wallet.approve:" + adjustment_id, payload=payload, action=perform)


@router.post("/reconciliation")
async def reconciliation(payload: ReconcileInput | None = None, ctx=FINANCE_RECONCILE):
    day = (payload.business_date if payload and payload.business_date else datetime.now(UTC).date()).isoformat()
    return await command(ctx, "finance.reconcile", payload={"date": day},
                         action=lambda: reconcile(ctx.db, business_date=day))


@router.get("/reconciliation")
async def runs(cursor: str = "", ctx=FINANCE_RECONCILE):
    return await page(ctx.db, ReconciliationRun, cursor=cursor,
                      fields=("id", "business_date", "status", "summary"))


@router.get("/reconciliation/{run_id}/diffs")
async def differences(run_id: str, cursor: str = "", ctx=FINANCE_RECONCILE):
    rows = await ctx.db.scalars(select(ReconciliationDiff).where(ReconciliationDiff.run_id == run_id,
        ReconciliationDiff.id > cursor).order_by(ReconciliationDiff.id).limit(PAGE_SIZE + 1))
    rows = list(rows)
    fields = ("id", "entity_id", "kind", "expected", "actual", "status", "resolution_ref", "version")
    return {"items": [view(row, fields) for row in rows[:PAGE_SIZE]],
            "next_cursor": rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None}
