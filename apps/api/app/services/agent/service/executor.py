"""One independently recorded operation per call; uncertain writes are never replayed."""

import asyncio
from datetime import UTC, datetime, timedelta

from app.services.agent.service.contracts import (
    Environment, LedgerEntry, OperationCall, Receipt, Task,
)
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.recovery import apply_recovery
from app.services.agent.service.store import TaskStore

OPERATION_COMPLETION_GRACE_SECONDS = 5

class Executor:
    def __init__(self, registry: OperationRegistry, store: TaskStore) -> None:
        self.registry = registry
        self.store = store

    async def execute(self, task: Task, call: OperationCall, *, env: Environment) -> Receipt:
        self._validate(task, call, env=env)
        previous = next((e for e in task.ledger if e.call.key == call.key), None)
        if previous is not None:
            if previous.call != call:
                raise ValueError("Idempotency key reused with different input")
            return previous.receipt or Receipt(status="unknown", error="reconcile_required")
        if task.calls_used >= task.max_calls:
            raise ValueError("task_budget_exhausted")
        op = self.registry.operations[call.operation_id]
        deadline = datetime.now(UTC) + timedelta(
            seconds=op.timeout_seconds + OPERATION_COMPLETION_GRACE_SECONDS,
        )
        entry = LedgerEntry(call=call, operation_version=op.version, deadline_at=deadline)
        task.ledger.append(entry)
        task.calls_used += 1
        await self.store.save(task)
        receipt = await self._invoke(call)
        entry.status, entry.receipt = receipt.status, receipt
        if receipt.evidence is not None and receipt.status in {"succeeded", "mock"}:
            task.evidence.append(receipt.evidence)
        apply_recovery(task, call, op=self.registry.operations[call.operation_id], receipt=receipt)
        await self.store.save(task)
        return receipt

    def _validate(self, task: Task, call: OperationCall, *, env: Environment) -> None:
        if task.scope != env.scope:
            raise PermissionError("scope_mismatch")
        if task.status != "active":
            raise ValueError("task_not_active")
        rejection = self.registry.rejection(call, env)
        if rejection:
            raise PermissionError(rejection)
        op = self.registry.operations[call.operation_id]
        uncertain = any(e.status in {"running", "unknown"} for e in task.ledger)
        if uncertain and op.effect != "read":
            raise ValueError("reconcile_required")

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
