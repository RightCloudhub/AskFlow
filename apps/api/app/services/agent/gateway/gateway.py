"""The Action Gateway: one enforcement point for policy, idempotency and the ledger (arch §4.4)."""

from app.services.agent.gateway.capabilities import CapabilitySpec
from app.services.agent.gateway.context import ExecContext
from app.services.agent.gateway.idempotency import args_hash, derive_key
from app.services.agent.gateway.ledger import (
    STATUS_COMPENSATED,
    STATUS_EXECUTED,
    STATUS_INTENT,
    STATUS_OUTCOME_UNKNOWN,
    STATUS_VERIFIED,
    LedgerAppend,
    LedgerStore,
)
from app.services.agent.gateway.policy import PolicyDecision, PolicyEngine

COMPENSABLE_STATUSES = frozenset({STATUS_EXECUTED, STATUS_OUTCOME_UNKNOWN})


class ActionGateway:
    def __init__(self, ledger: LedgerStore, policy: PolicyEngine | None = None) -> None:
        self.ledger, self.policy = ledger, policy or PolicyEngine()

    def key_for(self, *, scope_id: str, step: str, capability: CapabilitySpec, args: dict) -> str:
        return derive_key(scope_id=scope_id, step=step, capability=capability.name, args=args)

    def evaluate(
        self, *, capability: CapabilitySpec, args: dict, ctx: ExecContext
    ) -> PolicyDecision:
        return self.policy.evaluate(
            capability=capability,
            args=args,
            assurance=ctx.assurance,
            has_confirmation=ctx.has_confirmation,
        )

    async def record_decision(
        self,
        *,
        capability: CapabilitySpec,
        args: dict,
        ctx: ExecContext,
        decision: PolicyDecision,
        status: str,
        db=None,
        external_ref: str | None = None,
        error: dict | None = None,
        latency_ms: int | None = None,
    ):
        """Append DENIED / NEEDS_CONFIRMATION / INTENT rows (write-ahead before the call)."""
        key = self.key_for(
            scope_id=scope_id_for(ctx), step=ctx.step, capability=capability, args=args
        )
        entry = LedgerAppend(
            organization_id=ctx.scope.organization_id,
            customer_id=ctx.scope.customer_id,
            capability=capability.name,
            capability_version=capability.version,
            args_hash=args_hash(args),
            idempotency_key=key,
            policy_decision=decision.to_dict(),
            policy_version=decision.version,
            status=status,
            actor=ctx.actor,
            task_id=ctx.task_id,
            turn_id=ctx.turn_id,
            step=ctx.step,
            external_ref=external_ref,
            error=error,
            latency_ms=latency_ms,
        )
        if db is not None:
            return await self.ledger.append_in_transaction(db, entry)
        return await self.ledger.append(entry)

    async def record_intent(
        self, *, capability: CapabilitySpec, args: dict, ctx: ExecContext, decision: PolicyDecision, db=None
    ):
        return await self.record_decision(
            capability=capability, args=args, ctx=ctx, decision=decision, status=STATUS_INTENT, db=db
        )

    async def record_outcome(
        self,
        *,
        key: str,
        status: str,
        db=None,
        external_ref: str | None = None,
        error: dict | None = None,
        latency_ms: int | None = None,
    ):
        return await self.ledger.transition(
            key, status, db=db, external_ref=external_ref, error=error, latency_ms=latency_ms
        )

    async def prior_status(self, key: str, *, db=None) -> str | None:
        row = await self.ledger.current(key, db=db)
        return row.status if row is not None else None

    async def record_verified(self, task, *, registry=None, db=None) -> int:
        """After application verification, mark EXECUTED write capabilities VERIFIED."""
        marked = 0
        for entry in task.ledger:
            if entry.status != "succeeded":
                continue
            if registry is not None:
                op = registry.operations.get(entry.call.operation_id)
                if op is None or op.effect == "read":
                    continue
            key = derive_key(
                scope_id=task.task_id,
                step=entry.call.key,
                capability=entry.call.operation_id,
                args=entry.call.arguments,
            )
            current = await self.ledger.current(key, db=db)
            if current is None or current.status != "EXECUTED":
                continue
            await self.ledger.transition(key, STATUS_VERIFIED, db=db)
            marked += 1
        return marked

    async def record_compensated(self, key: str, *, db=None, error: dict | None = None):
        """Mark a prior write COMPENSATED; only executed or unknown writes may transition."""
        current = await self.ledger.current(key, db=db)
        if current is None or current.status not in COMPENSABLE_STATUSES:
            return None
        return await self.ledger.transition(key, STATUS_COMPENSATED, db=db, error=error)


def scope_id_for(ctx: ExecContext) -> str:
    return ctx.task_id or ctx.turn_id or ctx.scope.customer_id
