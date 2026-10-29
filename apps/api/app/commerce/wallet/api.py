"""Owner-filtered balances, journal references and mock topups."""

from fastapi import APIRouter

from app.commerce.core.commands import command
from app.commerce.core.deps import MallContext
from app.commerce.core.schemas import PositiveCents, Schema
from app.commerce.wallet.service import WalletService
from app.commerce.wallet.topups import create
from app.services.agent.gateway.idempotency import args_hash

router = APIRouter()


class TopupInput(Schema):
    amount_cents: PositiveCents


@router.get("")
async def balance(ctx: MallContext):
    return await WalletService(ctx.db).balance(ctx.user.id)


@router.get("/entries")
async def entries(ctx: MallContext, cursor: str = ""):
    return await WalletService(ctx.db).entries(ctx.user.id, cursor=cursor)


@router.post("/topups")
async def topup(payload: TopupInput, ctx: MallContext):
    key = args_hash({"user_id": ctx.user.id, "key": ctx.key})
    return await command(ctx, "wallet.topup", payload=payload,
        action=lambda: create(ctx.db, ctx.user.id, amount_cents=payload.amount_cents, key=key))
