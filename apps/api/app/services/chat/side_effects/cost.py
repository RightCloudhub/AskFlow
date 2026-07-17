"""Persist cost ledger best-effort."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext


class CostSideEffect:
    key = "cost"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        try:
            from app.services.agent.cost.ledger import CostLedger
            from app.services.agent.cost.store import CostStore

            ledger = CostLedger(turn.run_id)
            for e in (turn.cost or {}).get("entries") or []:
                ledger.record(
                    purpose=e.get("purpose", ""),
                    model=e.get("model", ""),
                    prompt_tokens=int(e.get("prompt_tokens") or 0),
                    completion_tokens=int(e.get("completion_tokens") or 0),
                )
            await CostStore(turn.db).persist_ledger(ledger)
        except Exception:
            pass
        return se
