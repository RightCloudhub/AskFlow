"""Persist cost entries and aggregate for Admin (PRD §12.2 cost aggregates)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost_entry import CostLedgerEntry
from app.services.agent.cost.ledger import CostLedger


class CostStore:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def persist_ledger(self, ledger: CostLedger) -> int:
        n = 0
        try:
            for e in ledger.entries:
                self.db.add(
                    CostLedgerEntry(
                        run_id=ledger.run_id,
                        purpose=e.purpose,
                        model=e.model,
                        prompt_tokens=e.prompt_tokens,
                        completion_tokens=e.completion_tokens,
                        estimated_usd=e.estimated_usd,
                    )
                )
                n += 1
            await self.db.flush()
        except Exception:
            return 0
        return n

    async def aggregate(self) -> dict[str, Any]:
        by_purpose = await self.db.execute(
            select(
                CostLedgerEntry.purpose,
                func.sum(CostLedgerEntry.prompt_tokens),
                func.sum(CostLedgerEntry.completion_tokens),
                func.sum(CostLedgerEntry.estimated_usd),
                func.count(),
            ).group_by(CostLedgerEntry.purpose)
        )
        by_model = await self.db.execute(
            select(
                CostLedgerEntry.model,
                func.sum(CostLedgerEntry.prompt_tokens),
                func.sum(CostLedgerEntry.completion_tokens),
                func.sum(CostLedgerEntry.estimated_usd),
                func.count(),
            ).group_by(CostLedgerEntry.model)
        )
        return {
            "by_purpose": [
                {
                    "purpose": r[0],
                    "prompt_tokens": int(r[1] or 0),
                    "completion_tokens": int(r[2] or 0),
                    "estimated_usd": float(r[3] or 0),
                    "calls": int(r[4] or 0),
                }
                for r in by_purpose.all()
            ],
            "by_model": [
                {
                    "model": r[0],
                    "prompt_tokens": int(r[1] or 0),
                    "completion_tokens": int(r[2] or 0),
                    "estimated_usd": float(r[3] or 0),
                    "calls": int(r[4] or 0),
                }
                for r in by_model.all()
            ],
        }
