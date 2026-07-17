"""Default full-profile handlers for unit tests without AppContext."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.services.agent.pipeline.context import PipelineResult, TurnContext
from app.services.agent.pipeline.handlers.clarify import handle_clarify
from app.services.agent.pipeline.handlers.handoff import handle_handoff
from app.services.agent.pipeline.handlers.rag import handle_rag
from app.services.agent.pipeline.handlers.refuse import handle_refuse
from app.services.agent.pipeline.handlers.ticket import handle_ticket
from app.services.agent.pipeline.handlers.tool import handle_tool
from app.plugins.types import SideEffectHandler

RouteHandlerFn = Callable[[TurnContext], Awaitable[PipelineResult]]


def default_route_handlers() -> dict[str, RouteHandlerFn]:
    return {
        "clarify": handle_clarify,
        "refuse": handle_refuse,
        "rag": handle_rag,
        "tool": handle_tool,
        "ticket": handle_ticket,
        "handoff": handle_handoff,
    }


def default_side_effects() -> dict[str, SideEffectHandler]:
    # Lazy imports avoid pipeline ↔ chat circular import
    from app.services.chat.side_effects.cost import CostSideEffect
    from app.services.chat.side_effects.gap import GapSideEffect
    from app.services.chat.side_effects.handoff import HandoffSideEffect
    from app.services.chat.side_effects.ticket import TicketSideEffect

    handlers: list[SideEffectHandler] = [
        TicketSideEffect(),
        HandoffSideEffect(),
        GapSideEffect(),
        CostSideEffect(),
    ]
    return {h.key: h for h in handlers}


def resolve_route_handlers() -> dict[str, Any]:
    from app.plugins.runtime import get_app_context

    ctx = get_app_context()
    # Loaded context wins even if empty (plugin-disabled profile)
    if ctx is not None:
        return dict(ctx.route_handlers)
    return dict(default_route_handlers())


def resolve_side_effects() -> dict[str, SideEffectHandler]:
    from app.plugins.runtime import get_app_context

    ctx = get_app_context()
    if ctx is not None:
        return dict(ctx.side_effect_handlers)
    return default_side_effects()
