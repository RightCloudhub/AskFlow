"""Operational view composes owned domain projections with permission filtering."""

from fastapi import APIRouter

from app.commerce.admin.permissions import permissions_for, require
from app.commerce.core.services import enabled, service

ORDER_READ = require("order:read")

router = APIRouter()


@router.get("/dashboard")
async def dashboard(ctx=ORDER_READ):
    permissions = await permissions_for(ctx.db, ctx.user)
    result = await service("order", ctx.db).summary() if enabled("order") else {}
    if enabled("wallet") and "wallet:read" in permissions:
        result["wallet_liability_cents"] = await service("wallet", ctx.db).total_liability()
    if enabled("referral") and "risk:review" in permissions:
        result.update(await service("referral", ctx.db).summary())
    if enabled("support") and "support:read" in permissions:
        from app.services.ticket.repository.service import TicketRepository

        result["open_tickets"] = await TicketRepository(ctx.db).count_open()
    return result
