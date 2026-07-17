"""Launch Card CRUD (PRD E21 / §12.2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.launch_card import LaunchCard


class LaunchCardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        title: str,
        change_summary: str = "",
        expected_metrics: dict[str, Any] | None = None,
        created_by: str | None = None,
        notes: str = "",
    ) -> LaunchCard:
        card = LaunchCard(
            title=title,
            change_summary=change_summary,
            expected_metrics=expected_metrics or {},
            measured_metrics={},
            created_by=created_by,
            notes=notes,
            status="draft",
        )
        self.db.add(card)
        await self.db.flush()
        await self.db.refresh(card)
        return card

    async def list_cards(self) -> list[LaunchCard]:
        result = await self.db.execute(select(LaunchCard).order_by(LaunchCard.created_at.desc()))
        return list(result.scalars().all())

    async def get(self, card_id: str) -> LaunchCard | None:
        return await self.db.get(LaunchCard, card_id)

    async def fill_measured(
        self, card_id: str, measured: dict[str, Any], *, status: str = "measured"
    ) -> LaunchCard:
        card = await self.db.get(LaunchCard, card_id)
        if card is None:
            raise ValueError("not_found")
        card.measured_metrics = measured
        card.status = status
        await self.db.flush()
        await self.db.refresh(card)
        return card
