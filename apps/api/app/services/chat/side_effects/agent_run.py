"""Persist Agent run steps for admin replay (S-08)."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext
from app.services.agent.run_store import AgentRunStore, build_run_steps


class AgentRunSideEffect:
    key = "agent_run"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        try:
            flags = list(getattr(turn, "flags", None) or se.get("flags") or [])
            cost = turn.cost if isinstance(turn.cost, dict) else {}
            steps = build_run_steps(
                route=turn.route or "",
                intent=turn.intent,
                flags=flags,
                cost=cost,
                refused=bool(turn.refused),
            )
            summary = {
                "estimated_usd": cost.get("estimated_usd")
                or cost.get("total_estimated_usd")
                or 0,
                "entry_count": len(cost.get("entries") or []),
            }
            await AgentRunStore(turn.db).save(
                run_id=turn.run_id,
                conversation_id=turn.conversation_id,
                user_id=turn.user_id,
                route=turn.route or "",
                intent=turn.intent,
                refused=bool(turn.refused),
                flags=flags,
                steps=steps,
                cost_summary=summary,
            )
            se = {**se, "agent_run_saved": True, "run_id": turn.run_id}
        except Exception:
            se = {**se, "agent_run_saved": False}
        return se
