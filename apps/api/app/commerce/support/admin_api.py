"""Authorized customer support snapshots contain no delivery addresses or secrets."""

from fastapi import APIRouter
from sqlalchemy import select

from app.commerce.admin.permissions import require
from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.schemas import view
from app.commerce.support.models import SupportLink

router = APIRouter()


@router.get("")
async def links(cursor: str = "", ctx=require("support:read")):
    rows = list(await ctx.db.scalars(select(SupportLink).where(SupportLink.id > cursor)
                                    .order_by(SupportLink.id).limit(PAGE_SIZE)))
    return {"items": [view(row, ("id", "conversation_id", "order_id", "ticket_id", "snapshot")) for row in rows],
            "next_cursor": rows[-1].id if len(rows) == PAGE_SIZE else None}
