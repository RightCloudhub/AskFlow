"""Handoff inbox + pipeline + side-effect."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class HandoffPlugin:
    id = "handoff"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.handoffs.routes import router as handoffs_router
        from app.services.agent.pipeline.handlers.handoff import handle_handoff
        from app.services.chat.side_effects.handoff import HandoffSideEffect

        ctx.admin_router.include_router(handoffs_router, prefix="/handoffs", tags=["handoffs"])
        ctx.register_route_handler("handoff", handle_handoff)
        ctx.register_side_effect(HandoffSideEffect())
        ctx.add_nav(AdminNavItem("handoff", "/admin/handoffs", "接管", order=40))
