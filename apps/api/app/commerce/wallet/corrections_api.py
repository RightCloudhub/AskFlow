"""Audited finance review and two-operator reversal commands."""

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select

from app.commerce.account.mfa import require_step_up
from app.commerce.admin.permissions import require
from app.commerce.core.commands import command
from app.commerce.core.constants import NAME_SIZE, PAGE_SIZE
from app.commerce.core.schemas import Schema, Versioned, view
from app.commerce.wallet import corrections
from app.commerce.wallet.reversal_models import ReversalRequest

FINANCE_RECONCILE = require("finance:reconcile")
WALLET_ADJUST = require("wallet:adjust")
WALLET_APPROVE = require("wallet:approve")
WALLET_READ = require("wallet:read")

router = APIRouter()


class ReversalInput(Schema):
    journal_id: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=NAME_SIZE)
    step_up_token: str


class ReversalApproval(Versioned):
    approved: bool
    step_up_token: str


class DifferenceReview(Versioned):
    reference: str = Field(min_length=1, max_length=NAME_SIZE)
    reason: str = Field(min_length=1, max_length=NAME_SIZE)


@router.post("/reversals")
async def request(payload: ReversalInput, ctx=WALLET_ADJUST):
    require_step_up(ctx, payload.step_up_token, purpose="wallet_reversal")
    return await command(ctx, "wallet.reversal", payload=payload,
                         action=lambda: corrections.request_reversal(ctx, payload))


@router.get("/reversals")
async def requests(cursor: str = "", ctx=WALLET_READ):
    rows = list(await ctx.db.scalars(select(ReversalRequest).where(ReversalRequest.id > cursor)
        .order_by(ReversalRequest.id).limit(PAGE_SIZE + 1)))
    return {"items": [view(row, corrections.FIELDS) for row in rows[:PAGE_SIZE]],
            "next_cursor": rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None}


@router.post("/reversals/{request_id}/approve")
async def approve(request_id: str, payload: ReversalApproval, ctx=WALLET_APPROVE):
    require_step_up(ctx, payload.step_up_token, purpose="wallet_approve")
    return await command(ctx, "wallet.reversal_approve:" + request_id, payload=payload,
                         action=lambda: corrections.approve_reversal(ctx, request_id, payload))


@router.post("/differences/{difference_id}/review")
async def review(difference_id: str, payload: DifferenceReview, ctx=FINANCE_RECONCILE):
    return await command(ctx, "finance.review:" + difference_id, payload=payload,
                         action=lambda: corrections.resolve_difference(ctx, difference_id, payload))
