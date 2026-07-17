"""Knowledge gap radar (PRD §4.9) — best-effort, never blocks chat."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import GapStatus
from app.models.knowledge import KnowledgeGap


def normalize_question(q: str) -> str:
    s = (q or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[？?！!。．.]+$", "", s)
    return s[:512]


class GapService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        question: str,
        *,
        intent: str | None = None,
        conversation_id: str | None = None,
        reason: str | None = None,
    ) -> KnowledgeGap | None:
        try:
            norm = normalize_question(question)
            if not norm:
                return None
            result = await self.db.execute(
                select(KnowledgeGap).where(
                    KnowledgeGap.normalized_question == norm,
                    KnowledgeGap.status == GapStatus.OPEN.value,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                existing.hit_count = int(existing.hit_count or 0) + 1
                await self.db.flush()
                return existing

            gap = KnowledgeGap(
                question=question[:2000],
                normalized_question=norm,
                intent=intent,
                conversation_id=conversation_id,
                reason=reason,
            )
            self.db.add(gap)
            await self.db.flush()
            await self.db.refresh(gap)
            return gap
        except Exception:
            return None

    async def list_open(self) -> list[KnowledgeGap]:
        result = await self.db.execute(
            select(KnowledgeGap)
            .where(KnowledgeGap.status == GapStatus.OPEN.value)
            .order_by(KnowledgeGap.hit_count.desc(), KnowledgeGap.created_at.desc())
        )
        return list(result.scalars().all())

    async def dismiss(self, gap_id: str) -> KnowledgeGap | None:
        gap = await self.db.get(KnowledgeGap, gap_id)
        if gap is None:
            return None
        gap.status = GapStatus.DISMISSED.value
        await self.db.flush()
        await self.db.refresh(gap)
        return gap

    async def mark_promoted(self, gap_id: str) -> KnowledgeGap | None:
        gap = await self.db.get(KnowledgeGap, gap_id)
        if gap is None:
            return None
        gap.status = GapStatus.PROMOTED.value
        await self.db.flush()
        await self.db.refresh(gap)
        return gap
