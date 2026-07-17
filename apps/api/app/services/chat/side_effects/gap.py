"""Knowledge gap radar on weak-evidence refusal (not out_of_scope)."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext


class GapSideEffect:
    key = "gap"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        # Triggered on refused RAG-like answers, not OOS refuse route
        if not turn.refused:
            return se
        if turn.intent == "out_of_scope" or turn.route == "refuse":
            return se
        try:
            from app.services.knowledge.gap.service import GapService

            reason = "refused"
            if isinstance(turn.verification, dict):
                reason = turn.verification.get("result") or reason
            gap = await GapService(turn.db).record(
                turn.content,
                intent=turn.intent,
                conversation_id=turn.conversation_id,
                reason=reason,
            )
            if gap is not None:
                se["gap_id"] = gap.id
        except Exception:
            pass
        return se
