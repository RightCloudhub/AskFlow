"""Customer administration reuses users and revokes sessions when disabling."""

from fastapi import APIRouter
from sqlalchemy import select

from app.commerce.account.reset_api import router as reset_router
from app.commerce.account.sessions import revoke_all
from app.commerce.admin.permissions import require
from app.commerce.core.commands import command
from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.schemas import Schema, view
from app.models.user import User
from app.services.users.admin import UserAdminService

router = APIRouter()

router.include_router(reset_router)


class UserState(Schema):
    active: bool


@router.get("")
async def users(cursor: str = "", ctx=require("user:manage")):
    rows = list(await ctx.db.scalars(select(User).where(User.id > cursor).order_by(User.id).limit(PAGE_SIZE)))
    return {"items": [view(row, ("id", "username", "role", "is_active")) for row in rows],
            "next_cursor": rows[-1].id if len(rows) == PAGE_SIZE else None}


@router.post("/{user_id}/state")
async def state(user_id: str, payload: UserState, ctx=require("user:manage")):
    if user_id == ctx.user.id:
        raise MallError("cannot_disable_self")

    async def perform():
        row = await UserAdminService(ctx.db).set_active(user_id, payload.active, actor_id=ctx.user.id)
        if not payload.active:
            await revoke_all(ctx.db, user_id)
        return {"id": row.id, "active": row.is_active}

    return await command(ctx, "account.state:" + user_id, payload=payload, action=perform)
