"""One independently recorded operation per call; uncertain writes are never replayed."""

import asyncio
from datetime import UTC, datetime, timedelta

from app.services.agent.service.contracts import (
    Environment,
    LedgerEntry,
    OperationCall,
    Receipt,
    Task,
)
from app.services.agent.service.recovery import apply_recovery
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.selection import budget_stop, fresh_environment, over_budget
from app.services.agent.service.store import TaskStore

OPERATION_COMPLETION_GRACE_SECONDS = 5


class Executor:
    def __init__(self, registry: OperationRegistry, store: TaskStore) -> None:
        self.registry = registry
        self.store = store

    async def execute(
        self,
        task: Task,
        call: OperationCall,
        *,
        env: Environment,
        estimated_cost: float | None = None,
    ) -> Receipt:
        env = fresh_environment(env)
        self._validate(task, call, env=env)
        previous = next((e for e in task.ledger if e.call.key == call.key), None)
        if previous is not None:
            if previous.call != call:
                raise ValueError("Idempotency key reused with different input")
            return previous.receipt or Receipt(status="unknown", error="reconcile_required")
        if budget_stop(task) or over_budget(task, estimated_cost):
            raise ValueError("task_budget_exhausted")
        op = self.registry.operations[call.operation_id]
        deadline = datetime.now(UTC) + timedelta(
            seconds=op.timeout_seconds + OPERATION_COMPLETION_GRACE_SECONDS,
        )
        entry = LedgerEntry(call=call, operation_version=op.version, deadline_at=deadline)
        task.ledger.append(entry)
        task.calls_used += 1
        task.cost_used += estimated_cost or 0
        await self.store.save(task)
        receipt = await self._invoke(call)
        entry.status, entry.receipt = receipt.status, receipt
        self._track_progress(task, receipt)
        self._append_evidence(task, receipt)
        apply_recovery(task, call, op=self.registry.operations[call.operation_id], receipt=receipt)
        await self.store.save(task)
        return receipt

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
        except Exception:
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
