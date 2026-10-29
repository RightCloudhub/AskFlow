"""Two distinct authorized operators must request and approve an MFA reset."""

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import delete, select

from app.commerce.account.mfa import require_step_up
from app.commerce.account.models import RecoveryCode, SecurityReset
from app.commerce.account.repository import identity_by_id, security_for
from app.commerce.account.sessions import revoke_all
from app.commerce.admin.permissions import require
from app.commerce.core.commands import command
from app.commerce.core.constants import NAME_SIZE, PAGE_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.repository import cas
from app.commerce.core.schemas import Schema, Versioned, view

router = APIRouter()
FIELDS = ("id", "user_id", "requested_by", "approved_by", "reason", "status", "version")


class ResetRequest(Schema):
    reason: str = Field(min_length=1, max_length=NAME_SIZE)
    step_up_token: str


class ResetApproval(Versioned):
    approved: bool
    step_up_token: str


@router.get("/mfa-resets")
async def requests(cursor: str = "", ctx=require("user:manage")):
    rows = await ctx.db.scalars(select(SecurityReset).where(SecurityReset.id > cursor)
                               .order_by(SecurityReset.id).limit(PAGE_SIZE))
    return {"items": [view(row, FIELDS) for row in rows]}


@router.post("/{user_id}/mfa-reset")
async def request(user_id: str, payload: ResetRequest, ctx=require("user:manage")):
    require_step_up(ctx, payload.step_up_token, purpose="mfa_reset_request")
    if await identity_by_id(ctx.db, user_id) is None:
        raise MallError("resource_not_found", status=404)

    async def perform():
        row = SecurityReset(user_id=user_id, requested_by=ctx.user.id, reason=payload.reason)
        ctx.db.add(row)
        await ctx.db.flush()
        return view(row, FIELDS)

    return await command(ctx, "mfa.reset_request:" + user_id, payload=payload, action=perform)


@router.post("/mfa-resets/{request_id}/approve")
async def approve(request_id: str, payload: ResetApproval, ctx=require("user:manage")):
    require_step_up(ctx, payload.step_up_token, purpose="mfa_reset_approve")

    async def perform():
        row = await ctx.db.scalar(select(SecurityReset).where(SecurityReset.id == request_id).with_for_update())
        if row is None:
            raise MallError("resource_not_found", status=404)
        if row.requested_by == ctx.user.id or row.user_id == ctx.user.id:
            raise MallError("mfa_reset_dual_control", status=403)
        if row.status != "pending" or row.version != payload.expected_version:
            raise MallError("version_conflict")
        if payload.approved:
            await reset(ctx.db, row.user_id)
        await cas(ctx.db, row, values={"status": "approved" if payload.approved else "rejected", "approved_by": ctx.user.id})
        await publish(ctx.db, row, event_type="mall.account.mfa_reset", payload={"user_id": row.user_id, "status": row.status})
        return view(row, FIELDS)

    return await command(ctx, "mfa.reset_approve:" + request_id, payload=payload, action=perform)


async def reset(db, user_id: str):
    await identity_by_id(db, user_id, lock=True)
    security = await security_for(db, user_id)
    security.mfa_enabled, security.totp_cipher, security.pending_totp_cipher = False, "", ""
    security.last_totp_step = -1
    await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))
    await revoke_all(db, user_id)
