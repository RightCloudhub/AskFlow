"""Cost ledger admin + side-effect persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class CostPlugin:
    id = "cost"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.costs.routes import router as costs_router
        from app.services.chat.side_effects.cost import CostSideEffect

        ctx.admin_router.include_router(costs_router, prefix="/costs", tags=["costs"])
        ctx.register_side_effect(CostSideEffect())
        ctx.add_nav(AdminNavItem("cost", "/admin/costs", "成本", order=93))
