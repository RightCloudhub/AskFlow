"""One independently recorded operation per call; uncertain writes are never replayed."""

import asyncio
import time
from datetime import UTC, datetime, timedelta

from app.services.agent.gateway.capabilities import CapabilitySpec, spec_for_operation
from app.services.agent.gateway.context import ExecContext
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.idempotency import args_hash
from app.services.agent.gateway.ledger import (
    STATUS_DENIED,
    STATUS_EXECUTED,
    STATUS_FAILED,
    STATUS_OUTCOME_UNKNOWN,
    LedgerStore,
)
from app.services.agent.service.contracts import (
    Environment,
    LedgerEntry,
    OperationCall,
    Receipt,
    Task,
)
from app.services.agent.service.executor_compensation import CompensationFlow
from app.services.agent.service.executor_parks import ParkFlow
from app.services.agent.service.recovery import apply_recovery
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.selection import budget_stop, fresh_environment, over_budget
from app.services.agent.service.store import TaskStore

OPERATION_COMPLETION_GRACE_SECONDS = 5
EXTERNAL_REF_KEYS = ("reference", "id", "refund_id", "ticket_id", "handoff_id")
MS_PER_SECOND = 1000
LEDGER_STATUS_BY_RECEIPT = {
    "succeeded": STATUS_EXECUTED,
    "mock": STATUS_EXECUTED,
    "failed": STATUS_FAILED,
    "unknown": STATUS_OUTCOME_UNKNOWN,
}


class Executor(CompensationFlow, ParkFlow):
    def __init__(self, registry: OperationRegistry, store: TaskStore) -> None:
        self.registry, self.store = registry, store
        self.gateway = ActionGateway(LedgerStore(store.sessions))

    async def execute(
        self,
        task: Task,
        call: OperationCall,
        *,
        env: Environment,
        estimated_cost: float | None = None,
        budget_exempt: bool = False,
    ) -> Receipt:
        env = fresh_environment(env)
        self._validate(task, call, env=env)
        previous = self._replay(task, call)
        if previous is not None:
            return previous
        if not budget_exempt and (budget_stop(task) or over_budget(task, estimated_cost)):
            raise ValueError("task_budget_exhausted")
        op = self.registry.operations[call.operation_id]
        spec = spec_for_operation(op)
        ctx = self._context(task, call, spec)
        decision = self.gateway.evaluate(capability=spec, args=call.arguments, ctx=ctx)
        if not decision.allow:
            await self._record_denied(spec=spec, call=call, ctx=ctx, decision=decision)
            raise PermissionError("policy_denied")
        if decision.requires_human_approval:
            return await self._park_for_approval(
                task=task, call=call, spec=spec, ctx=ctx, decision=decision
            )
        if decision.requires_confirmation:
            return await self._park_for_confirmation(
                task=task, call=call, spec=spec, ctx=ctx, decision=decision
            )
        return await self._run(
            task, call, op=op, spec=spec, ctx=ctx, decision=decision, estimated_cost=estimated_cost
        )

    @staticmethod
    def _replay(task: Task, call: OperationCall) -> Receipt | None:
        previous = next((e for e in task.ledger if e.call.key == call.key), None)
        if previous is None:
            return None
        if previous.call != call:
            raise ValueError("Idempotency key reused with different input")
        return previous.receipt or Receipt(status="unknown", error="reconcile_required")

    async def _record_denied(self, *, spec, call, ctx, decision) -> None:
        await self.gateway.record_decision(
            capability=spec,
            args=call.arguments,
            ctx=ctx,
            decision=decision,
            status=STATUS_DENIED,
            error={"reasons": list(decision.reasons)},
        )

    async def _run(self, task, call, *, op, spec, ctx, decision, estimated_cost) -> Receipt:
        deadline = datetime.now(UTC) + timedelta(
            seconds=op.timeout_seconds + OPERATION_COMPLETION_GRACE_SECONDS,
        )
        entry = LedgerEntry(call=call, operation_version=op.version, deadline_at=deadline)
        task.ledger.append(entry)
        task.calls_used += 1
        task.cost_used += estimated_cost or 0
        key = self.gateway.key_for(
            scope_id=task.task_id, step=call.key, capability=spec, args=call.arguments
        )
        await self.gateway.record_intent(
            capability=spec, args=call.arguments, ctx=ctx, decision=decision
        )
        await self.store.save(task)
        started = time.monotonic()
        receipt = await self._invoke(call)
        latency_ms = int((time.monotonic() - started) * MS_PER_SECOND)
        entry.status, entry.receipt = receipt.status, receipt
        self._track_progress(task, receipt)
        self._append_evidence(task, receipt)
        await self.gateway.record_outcome(
            key=key,
            status=LEDGER_STATUS_BY_RECEIPT[receipt.status],
            external_ref=_external_ref(receipt),
            error={"error": receipt.error} if receipt.error else None,
            latency_ms=latency_ms,
        )
        if receipt.status in {"succeeded", "mock"} and spec.is_write:
            self._consume_confirmation(task, call, spec)
        apply_recovery(task, call, op=op, receipt=receipt)
        await self.store.save(task)
        return receipt

    def _context(self, task: Task, call: OperationCall, spec: CapabilitySpec) -> ExecContext:
        return ExecContext(
            scope=task.scope,
            actor="agent",
            assurance=task.assurance_level,
            task_id=task.task_id,
            step=call.key,
            has_confirmation=self._confirmation_valid(task, call, spec),
        )

    @staticmethod
    def _confirmation_valid(task: Task, call: OperationCall, spec: CapabilitySpec) -> bool:
        digest = args_hash(call.arguments)
        return any(
            grant.capability == spec.name and grant.args_hash == digest
            for grant in task.confirmations
        )

    @staticmethod
    def _consume_confirmation(task: Task, call: OperationCall, spec: CapabilitySpec) -> None:
        digest = args_hash(call.arguments)
        task.confirmations = [
            grant
            for grant in task.confirmations
            if not (grant.capability == spec.name and grant.args_hash == digest)
        ]
        pending = task.pending_confirmation
        if pending is not None and pending.capability == spec.name:
            task.pending_confirmation = None

    def _validate(self, task: Task, call: OperationCall, *, env: Environment) -> None:
        if task.scope != env.scope:
            raise PermissionError("scope_mismatch")
        op = self.registry.operations.get(call.operation_id)
        replay = self._can_replay(task, op)
        if task.status != "active" and not replay:
            raise ValueError("task_not_active")
        rejection = self.registry.rejection(call, env)
        if rejection:
            raise PermissionError(rejection)
        self._validate_execution_state(task, call, replay=replay)

    def _validate_execution_state(self, task: Task, call: OperationCall, *, replay: bool) -> None:
        op = self.registry.operations[call.operation_id]
        if replay and any(e.call.key == call.key for e in task.ledger):
            return
        uncertain = any(e.status in {"running", "unknown"} for e in task.ledger)
        if uncertain and op.effect != "read":
            raise ValueError("reconcile_required")
        if task.status != "active":
            raise ValueError("task_not_active")

    @staticmethod
    def _can_replay(task: Task, op) -> bool:
        return bool(op and op.replay_receipts_when_waiting and task.status == "waiting_external")

    @staticmethod
    def _append_evidence(task: Task, receipt: Receipt) -> None:
        if receipt.evidence is not None and receipt.status in {"succeeded", "mock"}:
            task.evidence.append(receipt.evidence)

    @staticmethod
    def _track_progress(task: Task, receipt: Receipt) -> None:
        evidence = receipt.evidence
        fresh = bool(
            evidence
            and not evidence.simulated
            and receipt.status == "succeeded"
            and evidence.observed_at <= datetime.now(UTC) < evidence.expires_at
        )
        novel = fresh and not any(
            e.operation_id == evidence.operation_id and e.data == evidence.data
            for e in task.evidence
        )
        task.no_progress_cycles = 0 if novel else task.no_progress_cycles + 1

    async def _invoke(self, call: OperationCall) -> Receipt:
        op = self.registry.operations[call.operation_id]
        try:
            args = op.input_schema.model_validate(call.arguments, strict=True)
            request = call.model_copy(deep=True, update={"arguments": args.model_dump()})
            result = await asyncio.wait_for(op.handler(request), timeout=op.timeout_seconds)
            receipt = Receipt.model_validate(op.output_schema.model_validate(result).model_dump())
            return self._validate_receipt(call, receipt)
        except (TimeoutError, ConnectionError):
            status = "failed" if op.effect == "read" else "unknown"
            return Receipt(status=status, error_kind="transient", error="transport_failure")
        except Exception:  # noqa: BLE001 - any unexpected error is uncertain for writes
            # Invalid output is also uncertain: the external side effect may have happened.
            status = "failed" if op.effect == "read" else "unknown"
            return Receipt(status=status, error_kind="permanent", error="operation_failure")

    @staticmethod
    def _validate_receipt(call: OperationCall, receipt: Receipt) -> Receipt:
        evidence = receipt.evidence
        if evidence is not None and evidence.operation_id != call.operation_id:
            raise ValueError("Evidence operation mismatch")
        if evidence is not None and (receipt.status == "mock" or evidence.source == "mock"):
            evidence.simulated = True
        return receipt


def _external_ref(receipt: Receipt) -> str | None:
    evidence = receipt.evidence
    if evidence is None:
        return None
    for key in EXTERNAL_REF_KEYS:
        value = evidence.data.get(key)
        if value:
            return str(value)
    return None
