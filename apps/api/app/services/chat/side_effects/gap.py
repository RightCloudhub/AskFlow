"""Knowledge gap radar on weak-evidence refusal (not out_of_scope)."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext
from app.services.knowledge.gap.service import GapService

UNKNOWN_REASON = "refused"


def refusal_reason(verification: Any) -> str:
    """Why grounding refused (``zero_hit`` / ``weak_evidence``).

    ``verification["result"]`` is always ``"skipped"`` on a refusal, so it said nothing.
    """
    if isinstance(verification, dict):
        return str(verification.get("refusal_reason") or UNKNOWN_REASON)
    return UNKNOWN_REASON


class GapSideEffect:
    key = "gap"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        if not turn.refused:
            return se
        if turn.intent == "out_of_scope" or turn.route == "refuse":
            return se
        gap = await GapService(turn.db).record(
            turn.content,
            intent=turn.intent,
            conversation_id=turn.conversation_id,
            reason=refusal_reason(turn.verification),
        )
        if gap is not None:
            se["gap_id"] = gap.id
        return se
