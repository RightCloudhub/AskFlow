"""Materialize ticket create side-effect."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext
from app.schemas.ticket import TicketCreate
from app.services.ticket.repository.service import TicketRepository


class TicketSideEffect:
    key = "ticket"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        payload = se.get("ticket") or {}
        if payload.get("action") != "create":
            return se
        repo = TicketRepository(turn.db)
        t_payload = TicketCreate(
            title=payload["title"],
            description=payload.get("description", turn.content),
            type=payload.get("type", "fault_report"),
            priority=payload.get("priority", "high"),
            conversation_id=turn.conversation_id,
        )
        ticket, created = await repo.create_or_get_open(turn.user_id, t_payload)
        se["ticket"] = {
            **payload,
            "id": ticket.id,
            "created": created,
        }
        if created:
            await self._notify_created(turn, ticket)
        return se

    async def _notify_created(self, turn: ChatTurnContext, ticket: Any) -> None:
        from app.plugins.runtime import get_app_context

        ctx = get_app_context()
        if ctx is not None and not ctx.enabled("notify"):
            return
        try:
            from app.models.enums import NotifyEvent
            from app.services.notify.service import NotifyService

            await NotifyService(turn.db).emit_safe(
                NotifyEvent.TICKET_CREATED.value,
                {
                    "ticket_id": ticket.id,
                    "title": ticket.title,
                    "user_id": turn.user_id,
                },
            )
        except Exception:
            pass
