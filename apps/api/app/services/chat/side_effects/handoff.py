"""Materialize handoff enqueue side-effect."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext
from app.services.handoff.service import HandoffService


class HandoffSideEffect:
    key = "handoff"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        payload = se.get("handoff") or {}
        if payload.get("action") != "enqueue":
            return se
        hs = HandoffService(turn.db)
        handoff = await hs.enqueue(
            conversation_id=turn.conversation_id,
            user_id=turn.user_id,
            summary=payload.get("summary") or turn.content,
            intent=turn.intent or payload.get("intent") or "handoff",
        )
        se["handoff"] = {
            **payload,
            "id": handoff.id,
            "status": handoff.status,
            "intent": handoff.intent,
        }
        return se
