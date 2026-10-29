"""Operational view composes owned domain projections with permission filtering."""

from fastapi import APIRouter

from app.commerce.admin.permissions import permissions_for, require
from app.commerce.core.services import enabled, service

router = APIRouter()


@router.get("/dashboard")
async def dashboard(ctx=require("order:read")):
    permissions = await permissions_for(ctx.db, ctx.user)
    result = await service("order", ctx.db).summary() if enabled("order") else {}
    if enabled("wallet") and "wallet:read" in permissions:
        result["wallet_liability_cents"] = await service("wallet", ctx.db).total_liability()
    return result
