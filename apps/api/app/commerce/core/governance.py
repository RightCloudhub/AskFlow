"""Local writes share the existing confirmation and append-only Gateway ledger."""

from http import HTTPStatus
from uuid import NAMESPACE_URL, uuid5

from app.commerce.core.errors import MallError
from app.commerce.core.idempotency import execute
from app.core import database
from app.services.agent.gateway.capabilities import CapabilitySpec
from app.services.agent.gateway.confirmation import issue_confirmation, validate_confirmation
from app.services.agent.gateway.context import ExecContext
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.ledger import LedgerStore
from app.services.agent.gateway.policy import PolicyDecision, PolicyEngine
from app.services.agent.service.contracts import Scope

MALL_WRITES = frozenset({"mall.order.cancel", "mall.refund.submit", "refund.submit"})


class MallPolicy(PolicyEngine):
    def __init__(self, *, refund_limit: int):
        super().__init__()
        self.refund_limit = refund_limit

    def evaluate(self, *, capability, args, assurance, has_confirmation=False):
        result = super().evaluate(capability=capability, args=args, assurance=assurance,
                                  has_confirmation=has_confirmation)
        if capability.name not in {"refund.submit", "mall.refund.submit"}:
            return result
        return PolicyDecision(allow=result.allow, requires_confirmation=result.requires_confirmation,
            step_up_required=result.step_up_required, version=result.version,
            requires_human_approval=args.get("amount_cents", 0) > self.refund_limit,
            reasons=result.reasons)


async def governed(ctx, name: str, *, arguments: dict, confirmation: str, action):
    from app.commerce.admin.settings_service import value

    spec = CapabilitySpec(name=name, side_effect="irreversible_write",
                          required_assurance=2, requires_confirmation=True)
    execution = ExecContext(scope=Scope(organization_id="deployment", customer_id=ctx.user.id),
        actor="user", assurance=ctx.claims.get("assurance", 1),
        turn_id=str(uuid5(NAMESPACE_URL, ctx.user.id + ":" + ctx.key)),
        step=name, has_confirmation=bool(confirmation))
    policy = MallPolicy(refund_limit=await value(ctx.db, "mall_auto_refund_cents"))
    gateway = ActionGateway(LedgerStore(database.SessionLocal), policy)
    decision = gateway.evaluate(capability=spec, args=arguments, ctx=execution)
    if not decision.allow:
        await gateway.record_decision(capability=spec, args=arguments, ctx=execution,
                                      decision=decision, status="DENIED", db=ctx.db)
        raise MallError("step_up_required", status=HTTPStatus.FORBIDDEN, persist=True)
    if not confirmation:
        return await _confirmation(ctx, gateway, spec=spec, arguments=arguments,
                                   execution=execution, decision=decision)

    async def perform():
        valid = await validate_confirmation(ctx.db, confirmation, scope_id=ctx.user.id,
            step=name + ":" + ctx.key, args=arguments)
        if not valid:
            raise MallError("confirmation_invalid", status=HTTPStatus.FORBIDDEN)
        entry = await gateway.record_intent(capability=spec, args=arguments, ctx=execution,
                                            decision=decision, db=ctx.db)
        result = await action(decision.requires_human_approval)
        await gateway.record_outcome(key=entry.idempotency_key, status="EXECUTED", db=ctx.db,
                                     external_ref=result.get("id"))
        return result

    return await execute(ctx.db, scope=name + ":" + ctx.user.id, key=ctx.key,
                         arguments=arguments, action=perform)


async def _confirmation(ctx, gateway, *, spec, arguments, execution, decision):
    if not ctx.key:
        raise MallError("idempotency_key_required", status=HTTPStatus.BAD_REQUEST)
    token = await issue_confirmation(ctx.db, scope_id=ctx.user.id,
                                     step=spec.name + ":" + ctx.key, args=arguments)
    await gateway.record_decision(capability=spec, args=arguments, ctx=execution,
        decision=decision, status="NEEDS_CONFIRMATION", db=ctx.db)
    return {"status": "needs_confirmation", "confirmation_token": token.token,
            "expires_at": token.expires_at.isoformat(),
            "requires_human_approval": decision.requires_human_approval}
