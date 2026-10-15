"""Run declared compensations for plain op ids; mark the original ledger row (arch §4.6)."""

from app.services.agent.gateway.capabilities import automatic_compensation, spec_for_operation
from app.services.agent.service.contracts import OperationCall, Receipt

COMPENSATION_KEY_PREFIX = "compensate:"
SUCCEEDED_STATUSES = frozenset({"succeeded", "mock"})
UNCERTAIN_STATUSES = frozenset({"running", "unknown"})


class CompensationFlow:
    """Mixin: relies on ``self.registry``, ``self.store`` and ``self.gateway``."""

    async def compensate(self, task, *, original_key: str, env) -> Receipt | None:
        """Run the declared compensation for a succeeded write and mark its ledger row."""
        entry = self._compensable_entry(task, original_key)
        if entry is None:
            return None
        declared = self._declared_operation(entry)
        if declared is None:
            return None
        call = OperationCall(
            key=f"{COMPENSATION_KEY_PREFIX}{original_key}",
            operation_id=declared,
            arguments={**entry.call.arguments},
        )
        receipt = await self._invoke_compensation(task, call, env=env)
        if receipt.status in SUCCEEDED_STATUSES:
            await self._mark_compensated(task, entry)
        return receipt

    @staticmethod
    def _compensable_entry(task, original_key):
        entry = next((e for e in task.ledger if e.call.key == original_key), None)
        if entry is None or entry.status != "succeeded":
            return None
        if any(e.status in UNCERTAIN_STATUSES for e in task.ledger):
            return None  # uncertain writes must be reconciled before any new write
        return entry

    def _declared_operation(self, entry) -> str | None:
        op = self.registry.operations.get(entry.call.operation_id)
        if op is None or op.effect == "read":
            return None
        declared = automatic_compensation(op)
        if declared is None or declared not in self.registry.operations:
            return None
        return declared

    async def _invoke_compensation(self, task, call, *, env) -> Receipt:
        try:
            return await self.execute(task, call, env=env, budget_exempt=True)
        except PermissionError:
            return Receipt(status="failed", error_kind="permission", error="compensation_denied")

    async def _mark_compensated(self, task, entry) -> None:
        op = self.registry.operations[entry.call.operation_id]
        key = self.gateway.key_for(
            scope_id=task.task_id,
            step=entry.call.key,
            capability=spec_for_operation(op),
            args=entry.call.arguments,
        )
        await self.gateway.record_compensated(key)
