"""Ticket routes + pipeline + side-effect."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class TicketPlugin:
    id = "ticket"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.tickets.routes import router as admin_tickets_router
        from app.api.v1.tickets.routes import router as tickets_router
        from app.services.agent.pipeline.handlers.ticket import handle_ticket
        from app.services.chat.side_effects.ticket import TicketSideEffect

        ctx.api_router.include_router(tickets_router, prefix="/tickets", tags=["tickets"])
        ctx.admin_router.include_router(
            admin_tickets_router, prefix="/tickets", tags=["admin-tickets"]
        )
        ctx.register_route_handler("ticket", handle_ticket)
        ctx.register_side_effect(TicketSideEffect())
        ctx.add_nav(AdminNavItem("ticket", "/admin/tickets", "工单", order=50))
