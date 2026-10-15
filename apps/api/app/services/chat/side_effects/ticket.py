"""Materialize the ticket-create side effect through the action gateway."""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.types import ChatTurnContext
from app.schemas.ticket import TicketCreate
from app.services.agent.gateway.capabilities import spec_for_side_effect
from app.services.agent.gateway.context import ExecContext
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.ledger import (
    STATUS_DENIED,
    STATUS_EXECUTED,
    LedgerStore,
)
from app.services.agent.identity import customer_scope
from app.services.ticket.repository.service import TicketRepository

CAPABILITY = "ticket.create"
logger = logging.getLogger(__name__)


class TicketSideEffect:
    key = "ticket"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        payload = se.get("ticket") or {}
        if payload.get("action") != "create":
            return se
        gateway = ActionGateway(LedgerStore())
        spec = spec_for_side_effect(CAPABILITY)
        args = {
            "title": payload["title"],
            "type": payload.get("type", "fault_report"),
            "conversation_id": turn.conversation_id,
        }
        ctx = ExecContext(
            scope=customer_scope(turn.user_id), actor="agent", turn_id=turn.run_id, step=CAPABILITY
        )
        decision = gateway.evaluate(capability=spec, args=args, ctx=ctx)
        if not decision.allow:
            await gateway.record_decision(
                capability=spec,
                args=args,
                ctx=ctx,
                decision=decision,
                status=STATUS_DENIED,
                db=turn.db,
                error={"reasons": list(decision.reasons)},
            )
            se["ticket"] = {**payload, "denied": True}
            return se
        key = gateway.key_for(
            scope_id=turn.conversation_id, step=CAPABILITY, capability=spec, args=args
        )
        await gateway.record_intent(
            capability=spec, args=args, ctx=ctx, decision=decision, db=turn.db
        )
        repo = TicketRepository(turn.db)
        t_payload = TicketCreate(
            title=payload["title"],
            description=payload.get("description", turn.content),
            type=payload.get("type", "fault_report"),
            priority=payload.get("priority", "high"),
            conversation_id=turn.conversation_id,
        )
        ticket, created = await repo.create_or_get_open(turn.user_id, t_payload)
        await gateway.record_outcome(
            key=key, status=STATUS_EXECUTED, external_ref=ticket.id, db=turn.db
        )
        se["ticket"] = {**payload, "id": ticket.id, "created": created}
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
        except Exception:  # ticket notify is best-effort
            logger.debug("ticket notification failed", exc_info=True)
