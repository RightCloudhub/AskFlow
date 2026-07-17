"""Route resolution: ops config → built-in fallback → legal set (PRD §4.3.2)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import DEFAULT_INTENT_ROUTES, LEGAL_ROUTES, Intent, Route
from app.models.intent_config import IntentConfig


@dataclass
class ResolvedRoute:
    route: Route
    source: str  # ops | builtin | default
    intent: Intent


class RouteResolver:
    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        self._ops_cache: dict[str, str] | None = None

    async def resolve(self, intent: Intent) -> ResolvedRoute:
        ops = await self._load_ops_routes()
        if intent.value in ops:
            target = ops[intent.value]
            if target in {r.value for r in LEGAL_ROUTES}:
                return ResolvedRoute(route=Route(target), source="ops", intent=intent)

        builtin = DEFAULT_INTENT_ROUTES.get(intent, Route.RAG)
        return ResolvedRoute(route=builtin, source="builtin", intent=intent)

    async def _load_ops_routes(self) -> dict[str, str]:
        if self._ops_cache is not None:
            return self._ops_cache
        if self.db is None:
            self._ops_cache = {}
            return self._ops_cache
        result = await self.db.execute(
            select(IntentConfig).where(IntentConfig.enabled.is_(True))
        )
        rows = result.scalars().all()
        self._ops_cache = {row.intent: row.route for row in rows}
        return self._ops_cache

    def invalidate(self) -> None:
        self._ops_cache = None
