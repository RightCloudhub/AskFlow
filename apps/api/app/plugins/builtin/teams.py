"""Skill teams admin."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class TeamsPlugin:
    id = "teams"
    depends = ["handoff"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.teams.routes import router as teams_router

        ctx.admin_router.include_router(teams_router, prefix="/teams", tags=["teams"])
