"""Persist and query Agent runs for admin replay (PRD S-08)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.cost_entry import CostLedgerEntry

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200
USD_ROUND_DIGITS = 6


class AgentRunStore:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save(
        self,
        *,
        run_id: str,
        conversation_id: str | None,
        user_id: str | None,
        route: str,
        intent: str | None,
        refused: bool,
        flags: list[str],
        steps: list[dict[str, Any]],
        cost_summary: dict[str, Any],
    ) -> AgentRun:
        result = await self.db.execute(select(AgentRun).where(AgentRun.run_id == run_id))
        row = result.scalar_one_or_none()
        if row is None:
            row = AgentRun(run_id=run_id)
            self.db.add(row)
        row.conversation_id = conversation_id
        row.user_id = user_id
        row.route = route
        row.intent = intent
        row.refused = refused
        row.flags = list(flags or [])
        row.steps = list(steps or [])
        row.cost_summary = dict(cost_summary or {})
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get_by_run_id(self, run_id: str) -> AgentRun | None:
        result = await self.db.execute(select(AgentRun).where(AgentRun.run_id == run_id))
        return result.scalar_one_or_none()

    async def list_recent(self, *, limit: int = DEFAULT_LIST_LIMIT) -> list[AgentRun]:
        cap = max(1, min(limit, MAX_LIST_LIMIT))
        result = await self.db.execute(
            select(AgentRun).order_by(AgentRun.created_at.desc()).limit(cap)
        )
        return list(result.scalars().all())

    async def cost_for_run(self, run_id: str) -> dict[str, Any]:
        result = await self.db.execute(
            select(CostLedgerEntry).where(CostLedgerEntry.run_id == run_id)
        )
        entries = list(result.scalars().all())
        total_usd = sum(float(e.estimated_usd or 0) for e in entries)
        return {
            "run_id": run_id,
            "entries": [
                {
                    "purpose": e.purpose,
                    "model": e.model,
                    "prompt_tokens": e.prompt_tokens,
                    "completion_tokens": e.completion_tokens,
                    "estimated_usd": e.estimated_usd,
                }
                for e in entries
            ],
            "estimated_usd": round(total_usd, USD_ROUND_DIGITS),
            "entry_count": len(entries),
        }


def build_run_steps(
    *,
    route: str,
    intent: str | None,
    flags: list[str],
    cost: dict[str, Any] | None,
    refused: bool,
) -> list[dict[str, Any]]:
    """Build ordered key steps for replay without full LLM transcript."""
    steps: list[dict[str, Any]] = [
        {
            "kind": "route",
            "name": route,
            "detail": {"intent": intent, "refused": refused},
        }
    ]
    for f in flags or []:
        steps.append({"kind": "flag", "name": str(f), "detail": {}})
    for e in (cost or {}).get("entries") or []:
        steps.append(
            {
                "kind": "model",
                "name": str(e.get("purpose") or "model"),
                "detail": {
                    "model": e.get("model"),
                    "prompt_tokens": e.get("prompt_tokens"),
                    "completion_tokens": e.get("completion_tokens"),
                    "estimated_usd": e.get("estimated_usd"),
                },
            }
        )
    return steps
