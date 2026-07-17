"""Quality check aggregates for agent/ops (PRD E8 skeleton)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.conversation import Message
from app.models.feedback import Feedback
from app.models.handoff import HandoffSession

DEFAULT_LOW_SCORE = 40
SCORE_REFUSED = 30
SCORE_WEAK_FLAG = 15
SCORE_BASE = 100
LIST_DEFAULT = 30
LIST_MAX = 100
SCORE_MIN = 0
SCORE_MAX = 100


class QcService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def summary(self) -> dict[str, Any]:
        n_runs = await self._count(AgentRun)
        n_refused = await self._count_where(AgentRun, AgentRun.refused.is_(True))
        n_up = await self._count_where(Feedback, Feedback.rating == 1)
        n_down = await self._count_where(Feedback, Feedback.rating == -1)
        n_fb = n_up + n_down
        n_handoffs = await self._count(HandoffSession)
        n_messages = await self._count(Message)
        return {
            "agent_runs": n_runs,
            "refused_runs": n_refused,
            "refuse_rate": round(n_refused / n_runs, 4) if n_runs else 0.0,
            "thumbs_up": n_up,
            "thumbs_down": n_down,
            "thumbs_down_rate": round(n_down / n_fb, 4) if n_fb else 0.0,
            "handoffs": n_handoffs,
            "messages": n_messages,
            "quality_score_avg": await self._avg_run_score(),
        }

    async def _count(self, model: type) -> int:
        r = await self.db.execute(select(func.count()).select_from(model))
        return int(r.scalar_one() or 0)

    async def _count_where(self, model: type, *clauses: Any) -> int:
        stmt = select(func.count()).select_from(model)
        for c in clauses:
            stmt = stmt.where(c)
        r = await self.db.execute(stmt)
        return int(r.scalar_one() or 0)

    async def _avg_run_score(self) -> float | None:
        rows = await self.db.execute(select(AgentRun).limit(LIST_MAX))
        items = list(rows.scalars().all())
        if not items:
            return None
        scores = [self.score_run(r) for r in items]
        return round(sum(scores) / len(scores), 2)

    def score_run(self, run: AgentRun) -> int:
        """Deterministic 0–100 score from persisted run signals (no LLM)."""
        score = SCORE_BASE
        if run.refused:
            score -= SCORE_REFUSED
        for f in run.flags or []:
            fs = str(f).lower()
            if "weak" in fs or "blocked" in fs or "oos" in fs:
                score -= SCORE_WEAK_FLAG
        return max(SCORE_MIN, min(SCORE_MAX, score))

    async def low_quality_runs(
        self,
        *,
        threshold: int = DEFAULT_LOW_SCORE,
        limit: int = LIST_DEFAULT,
    ) -> list[dict[str, Any]]:
        cap = max(1, min(limit, LIST_MAX))
        scan = cap * 3
        result = await self.db.execute(
            select(AgentRun).order_by(AgentRun.created_at.desc()).limit(scan)
        )
        out: list[dict[str, Any]] = []
        for row in result.scalars().all():
            sc = self.score_run(row)
            if sc > threshold and not row.refused:
                continue
            out.append(
                {
                    "run_id": row.run_id,
                    "route": row.route,
                    "intent": row.intent,
                    "refused": row.refused,
                    "flags": row.flags or [],
                    "score": sc,
                    "conversation_id": row.conversation_id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
            if len(out) >= cap:
                break
        return out
