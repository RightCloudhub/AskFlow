"""Plugin SPI types (L2 — no third-party hot-load)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class AdminNavItem:
    plugin_id: str
    to: str
    label: str
    order: int = 100


@dataclass
class ChatTurnContext:
    """Context for side-effect materialization after pipeline."""

    db: AsyncSession
    conversation_id: str
    user_id: str
    content: str
    intent: str | None
    route: str
    refused: bool
    verification: dict[str, Any] | None
    run_id: str
    cost: dict[str, Any] | None
    flags: list[str] = field(default_factory=list)


@runtime_checkable
class SideEffectHandler(Protocol):
    key: str

    async def apply(
        self,
        se: dict[str, Any],
        turn: ChatTurnContext,
    ) -> dict[str, Any]:
        """Mutate/enrich side_effects dict; return updated se."""
        ...


@runtime_checkable
class Plugin(Protocol):
    id: str
    depends: list[str]

    def register(self, ctx: Any) -> None:
        """Register routes, handlers, tools, nav into AppContext."""
        ...


def empty_api_router() -> APIRouter:
    return APIRouter()


def empty_admin_router() -> APIRouter:
    return APIRouter(prefix="/admin")
