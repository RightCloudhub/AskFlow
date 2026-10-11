"""Persist the turn's real model calls to the cost ledger (budget seeds are skipped, D-04)."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext
from app.services.agent.cost.ledger import CostLedger
from app.services.agent.cost.store import CostStore

BUDGET_PHASE = "budget"


class CostSideEffect:
    key = "cost"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        entries = [
            e for e in (turn.cost or {}).get("entries", []) if e.get("phase") != BUDGET_PHASE
        ]
        if not entries:
            return se
        ledger = CostLedger(turn.run_id)
        for e in entries:
            ledger.record(
                purpose=e["purpose"],
                model=e["model"],
                prompt_tokens=int(e["prompt_tokens"]),
                completion_tokens=int(e["completion_tokens"]),
            )
        await CostStore(turn.db).persist_ledger(ledger)
        return se
