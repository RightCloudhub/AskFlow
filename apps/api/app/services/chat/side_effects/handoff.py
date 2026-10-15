"""Materialize the handoff-enqueue side effect through the action gateway."""

from __future__ import annotations

from typing import Any

from app.plugins.types import ChatTurnContext
from app.services.agent.gateway.capabilities import spec_for_side_effect
from app.services.agent.gateway.context import ExecContext
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.ledger import (
    STATUS_DENIED,
    STATUS_EXECUTED,
    LedgerStore,
)
from app.services.agent.identity import customer_scope
from app.services.handoff.service import HandoffService

CAPABILITY = "handoff.enqueue"


class HandoffSideEffect:
    key = "handoff"

    async def apply(self, se: dict[str, Any], turn: ChatTurnContext) -> dict[str, Any]:
        payload = se.get("handoff") or {}
        if payload.get("action") != "enqueue":
            return se
        gateway = ActionGateway(LedgerStore())
        spec = spec_for_side_effect(CAPABILITY)
        args = {"conversation_id": turn.conversation_id, "intent": turn.intent or "handoff"}
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
            se["handoff"] = {**payload, "denied": True}
            return se
        key = gateway.key_for(
            scope_id=turn.conversation_id, step=CAPABILITY, capability=spec, args=args
        )
        await gateway.record_intent(
            capability=spec, args=args, ctx=ctx, decision=decision, db=turn.db
        )
        hs = HandoffService(turn.db)
        handoff = await hs.enqueue(
            conversation_id=turn.conversation_id,
            user_id=turn.user_id,
            summary=payload.get("summary") or turn.content,
            intent=turn.intent or payload.get("intent") or "handoff",
        )
        await gateway.record_outcome(
            key=key, status=STATUS_EXECUTED, external_ref=handoff.id, db=turn.db
        )
        se["handoff"] = {
            **payload,
            "id": handoff.id,
            "status": handoff.status,
            "intent": handoff.intent,
        }
        return se
