"""Risk decisions remain auditable and cannot directly mint rewards."""

from http import HTTPStatus

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select

from app.commerce.admin.permissions import require
from app.commerce.core.commands import command
from app.commerce.core.constants import NAME_SIZE, PAGE_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas
from app.commerce.core.schemas import Versioned, view
from app.commerce.referral.models import RiskEvent

RISK_REVIEW = require("risk:review")

router = APIRouter()


class Review(Versioned):
    approved: bool
    note: str = Field(min_length=1, max_length=NAME_SIZE)


@router.get("")
async def risks(cursor: str = "", ctx=RISK_REVIEW):
    rows = list(await ctx.db.scalars(select(RiskEvent).where(RiskEvent.id > cursor)
                                    .order_by(RiskEvent.id).limit(PAGE_SIZE)))
    return {"items": [view(row, ("id", "user_id", "scope", "rule", "score", "decision", "version")) for row in rows],
            "next_cursor": rows[-1].id if len(rows) == PAGE_SIZE else None}


@router.post("/{event_id}/review")
async def review(event_id: str, payload: Review, ctx=RISK_REVIEW):
    async def perform():
        row = await ctx.db.get(RiskEvent, event_id)
        if row is None:
            raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
        if row.version != payload.expected_version:
            raise MallError("version_conflict")
        if row.decision != "review" or row.user_id == ctx.user.id:
            raise MallError("risk_review_conflict")
        await cas(ctx.db, row, values={"review_actor": ctx.user.id, "review_note": payload.note,
            "decision": "approved" if payload.approved else "rejected"})
        if row.scope == "referral" and row.signals_hash.get("reward_id"):
            from app.commerce.referral.service import ReferralService

            await ReferralService(ctx.db).reviewed(row.signals_hash["reward_id"], approved=payload.approved)
        return {"id": row.id, "decision": row.decision, "version": row.version}

    return await command(ctx, "risk.review:" + event_id, payload=payload, action=perform)
