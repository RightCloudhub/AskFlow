"""Run registered side-effect handlers in stable order."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext
from app.services.agent.pipeline.defaults import resolve_side_effects

# Explicit order: domain effects then gap, cost, run replay
HANDLER_ORDER = ("ticket", "handoff", "gap", "cost", "agent_run")


async def apply_side_effects(
    se: dict[str, Any],
    turn: ChatTurnContext,
) -> dict[str, Any]:
    handlers = resolve_side_effects()
    # Always run gap/cost/agent_run if registered even when key not in se
    always = {"gap", "cost", "agent_run"}
    for key in HANDLER_ORDER:
        handler = handlers.get(key)
        if handler is None:
            continue
        if key not in se and key not in always:
            continue
        se = await handler.apply(se, turn)
    return se
