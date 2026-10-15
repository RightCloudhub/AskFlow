"""Governed memory write: extract explicit facts after a turn; never block the reply (arch §9.8)."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext
from app.services.agent.memory.extract import extract_facts

# Blocked and transferred turns carry no customer statements to retain.
SKIP_ROUTES = frozenset({"blocked", "noop"})


class MemorySideEffect:
    key = "memory"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        from app.services.agent.memory.settings import MemorySettings

        if not MemorySettings().extract_enabled or turn.route in SKIP_ROUTES:
            return se
        proposals = extract_facts(turn.content or "")
        if not proposals:
            return se
        try:
            stored = await self._store(turn.db, turn.user_id, proposals)
        except Exception:  # noqa: BLE001 - optional memory must never block the turn (arch §8)
            return se
        if stored:
            se["memory"] = {"stored": stored}
        return se

    @staticmethod
    async def _store(db, user_id: str, proposals) -> list[str]:
        from app.services.agent.identity import customer_scope
        from app.services.agent.memory.facts import FactStore, MemoryRejected
        from app.services.agent.memory.store import MemoryConflict

        store = FactStore(None)
        scope = customer_scope(user_id)
        stored: list[str] = []
        for candidate in proposals:
            try:
                await store.remember_in_transaction(db, scope, candidate)
                stored.append(candidate.key)
            except (MemoryConflict, MemoryRejected, ValueError):
                continue
        return stored
