"""Versioned address mutations share durable idempotency and audit."""

from fastapi import APIRouter

from app.commerce.account.addresses import AddressService
from app.commerce.account.schemas import AddressInput, AddressPatch
from app.commerce.core.commands import command
from app.commerce.core.deps import MallContext
from app.commerce.core.errors import MallError
from app.commerce.core.schemas import Versioned

router = APIRouter()


@router.get("/addresses")
async def addresses(ctx: MallContext, cursor: str = ""):
    return await AddressService(ctx.db).list(ctx.user.id, cursor=cursor)


@router.post("/addresses")
async def add_address(payload: AddressInput, ctx: MallContext):
    return await command(ctx, "address.create", payload=payload,
        action=lambda: AddressService(ctx.db).save(ctx.user.id, payload))


@router.patch("/addresses/{address_id}")
async def edit_address(address_id: str, payload: AddressPatch, ctx: MallContext):
    return await command(ctx, "address.edit:" + address_id, payload=payload,
        action=lambda: AddressService(ctx.db).save(ctx.user.id, payload, address_id=address_id))


@router.delete("/addresses/{address_id}")
async def delete_address(address_id: str, payload: Versioned, ctx: MallContext):
    async def perform():
        row = await AddressService(ctx.db).get(ctx.user.id, address_id)
        if row.version != payload.expected_version:
            raise MallError("version_conflict")
        await ctx.db.delete(row)
        return {"id": address_id, "status": "deleted"}

    return await command(ctx, "address.delete:" + address_id, payload=payload, action=perform)
