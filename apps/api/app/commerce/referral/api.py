"""Customer invitation link and scoped reward history."""

from fastapi import APIRouter
from pydantic import Field

from app.commerce.core.commands import command
from app.commerce.core.constants import NAME_SIZE
from app.commerce.core.deps import MallContext
from app.commerce.core.repository import owned_page
from app.commerce.core.schemas import Schema, view
from app.commerce.referral.models import ReferralReward
from app.commerce.referral.service import ReferralService
from app.middleware.rate_limit import client_ip

router = APIRouter()


class Bind(Schema):
    code: str = Field(max_length=NAME_SIZE)
    device: str = Field(min_length=1, max_length=NAME_SIZE)


@router.post("/code")
async def code(ctx: MallContext):
    return await command(ctx, "referral.code", payload={},
                         action=lambda: ReferralService(ctx.db).code(ctx.user.id))


@router.post("/bind")
async def bind(payload: Bind, ctx: MallContext):
    return await command(ctx, "referral.bind", payload=payload,
        action=lambda: ReferralService(ctx.db).bind(ctx.user.id, code=payload.code,
                                                   device=payload.device, ip=client_ip(ctx.request)))


@router.get("/rewards")
async def rewards(ctx: MallContext, cursor: str = ""):
    rows, after = await owned_page(ctx.db, ReferralReward, owner_id=ctx.user.id, cursor=cursor)
    return {"items": [view(row, ("id", "amount_cents", "status", "eligible_at")) for row in rows], "next_cursor": after}
