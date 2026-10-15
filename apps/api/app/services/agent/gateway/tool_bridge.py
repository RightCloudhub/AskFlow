"""Govern legacy tool invocations: policy, ledger and denial through the gateway (arch §4.4)."""

from collections.abc import Awaitable, Callable
from typing import Any

from app.services.agent.gateway.capabilities import spec_for_tool
from app.services.agent.gateway.context import ExecContext
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.ledger import (
    STATUS_DENIED,
    STATUS_EXECUTED,
    STATUS_FAILED,
    STATUS_INTENT,
    LedgerStore,
)
from app.services.agent.identity import customer_scope

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
TOOL_OK_STATUSES = frozenset({"ok", "mock"})
TOOL_DENIED_MESSAGE = "权限不足，无法执行该工具。"


class ToolGatewayBridge:
    """One gateway decision + ledger pair per tool attempt; same transaction as the turn."""

    def __init__(self, *, turn_id: str, user_id: str, db, assurance: int = 1) -> None:
        self.gateway = ActionGateway(LedgerStore())
        self.scope = customer_scope(user_id)
        self.turn_id = turn_id
        self.db = db
        self.assurance = assurance
        self._calls: dict[str, int] = {}

    def wrap(self, name: str, handler: ToolHandler) -> ToolHandler:
        async def wrapped(arguments: dict[str, Any]) -> dict[str, Any]:
            return await self._invoke(name, handler, arguments)

        return wrapped

    async def _invoke(
        self, name: str, handler: ToolHandler, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        spec = spec_for_tool(name)
        self._calls[name] = self._calls.get(name, 0) + 1
        ctx = ExecContext(
            scope=self.scope,
            actor="agent",
            assurance=self.assurance,
            turn_id=self.turn_id,
            step=f"tool:{name}:{self._calls[name]}",
        )
        decision = self.gateway.evaluate(capability=spec, args=arguments, ctx=ctx)
        if not decision.allow:
            await self.gateway.record_decision(
                capability=spec,
                args=arguments,
                ctx=ctx,
                decision=decision,
                status=STATUS_DENIED,
                db=self.db,
                error={"reasons": list(decision.reasons)},
            )
            return {"status": "error", "error_class": "auth", "message": TOOL_DENIED_MESSAGE}
        key = self.gateway.key_for(
            scope_id=self.turn_id, step=ctx.step, capability=spec, args=arguments
        )
        await self.gateway.record_intent(
            capability=spec, args=arguments, ctx=ctx, decision=decision, db=self.db
        )
        try:
            result = await handler(arguments)
        except Exception:
            await self.gateway.record_outcome(
                key=key, status=STATUS_FAILED, db=self.db, error={"error": "tool_exception"}
            )
            raise
        status = STATUS_EXECUTED if str(result.get("status")) in TOOL_OK_STATUSES else STATUS_FAILED
        await self.gateway.record_outcome(key=key, status=status, db=self.db)
        return result


def build_tool_bridge(turn) -> ToolGatewayBridge | None:
    """Build a bridge for a pipeline turn when a DB session and user are available."""
    db = getattr(turn, "db", None)
    user_id = getattr(turn, "user_id", None)
    if db is None or not user_id:
        return None
    return ToolGatewayBridge(
        turn_id=turn.run_id,
        user_id=user_id,
        db=db,
        assurance=getattr(turn, "assurance", 1),
    )
