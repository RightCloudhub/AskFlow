"""Agent orchestration: classify debug + clarify/refuse handlers + run replay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

AGENT_NAV_ORDER = 95

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class AgentPlugin:
    id = "agent"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.agent_runs.routes import router as agent_runs_router
        from app.api.v1.agent.preferences import router as preferences_router
        from app.api.v1.agent.routes import router as agent_router
        from app.api.v1.agent.tasks import router as tasks_router, staff_router
        from app.services.agent.pipeline.handlers.clarify import handle_clarify
        from app.services.agent.pipeline.handlers.refuse import handle_refuse
        from app.services.chat.side_effects.agent_run import AgentRunSideEffect

        ctx.api_router.include_router(agent_router, prefix="/agent", tags=["agent"])
        ctx.api_router.include_router(preferences_router, prefix="/agent/preferences", tags=["agent"])
        ctx.api_router.include_router(tasks_router, prefix="/agent/tasks", tags=["agent"])
        ctx.admin_router.include_router(staff_router, prefix="/service-tasks", tags=["agent"])
        ctx.admin_router.include_router(
            agent_runs_router, prefix="/agent-runs", tags=["agent-runs"]
        )
        ctx.register_route_handler("clarify", handle_clarify)
        ctx.register_route_handler("refuse", handle_refuse)
        ctx.register_side_effect(AgentRunSideEffect())
        ctx.add_nav(AdminNavItem("agent", "/admin/agent-runs", "Agent Runs", order=AGENT_NAV_ORDER))
