"""Unified customer support entry and linked service history."""

from fastapi import APIRouter
from pydantic import Field

from app.commerce.core.commands import command
from app.commerce.core.constants import NAME_SIZE
from app.commerce.core.deps import MallContext
from app.commerce.core.repository import owned_page
from app.commerce.core.schemas import Schema, view
from app.commerce.support.models import SupportLink
from app.commerce.support.service import open_support

router = APIRouter()


class SupportRequest(Schema):
    title: str = Field(default="商城客服", min_length=1, max_length=NAME_SIZE)
    order_id: str | None = None
    refund_id: str | None = None
    wallet_journal_id: str | None = None
    ticket: bool = False
    handoff: bool = False


@router.post("")
async def create(payload: SupportRequest, ctx: MallContext):
    return await command(ctx, "support.open", payload=payload, action=lambda: open_support(ctx, payload))


@router.get("")
async def links(ctx: MallContext, cursor: str = ""):
    rows, after = await owned_page(ctx.db, SupportLink, owner_id=ctx.user.id, cursor=cursor)
    fields = ("id", "order_id", "refund_id", "conversation_id", "ticket_id", "created_at")
    return {"items": [view(row, fields) for row in rows], "next_cursor": after}
