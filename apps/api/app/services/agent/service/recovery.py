"""Errors become durable recovery signals, bounded retries or an owned waiting state."""

from datetime import UTC, datetime, timedelta

from app.services.agent.service.contracts import Operation, OperationCall, Receipt, RecoverySignal, Task

RETRY_BASE_SECONDS = 5
RECOVERY_REVIEW_SECONDS = 60
MAX_BACKOFF_SECONDS = 60
MAX_BACKOFF_EXPONENT = 4
READ_FAILURE_ACTIONS = {
    "transient": "retry", "unavailable": "fallback", "permission": "owner_review",
    "invalid_input": "ask_customer", "conflict": "fallback", "permanent": "owner_review",
    "unknown": "owner_review", "simulated": "fallback",
}


def apply_recovery(task: Task, call: OperationCall, *, op: Operation, receipt: Receipt) -> None:
    if receipt.status == "succeeded":
        return
    kind = receipt.error_kind or "permanent"
    if receipt.status == "unknown":
        kind = "unknown"
    if receipt.status == "mock":
        kind = "simulated"
    action = READ_FAILURE_ACTIONS[kind]
    if op.effect != "read":
        action = "reconcile" if kind == "unknown" else "owner_review"
    attempts = sum(e.call.operation_id == call.operation_id for e in task.ledger)
    if action == "retry" and attempts > op.max_retries:
        action = "fallback"
    signal = RecoverySignal(operation_id=call.operation_id, request_key=call.key,
                            kind=kind, action=action)
    task.recovery_signals.append(signal)
    _schedule(task, signal, attempts=attempts)


def _schedule(task: Task, signal: RecoverySignal, *, attempts: int) -> None:
    now = datetime.now(UTC)
    if signal.action == "fallback":
        signal.retry_at = now + timedelta(seconds=RECOVERY_REVIEW_SECONDS)
        return
    task.status = "waiting_external"
    task.wake_condition = f"{signal.action}:{signal.request_key}"
    task.review_at = now + timedelta(seconds=RECOVERY_REVIEW_SECONDS)
    if signal.action == "ask_customer":
        task.status = "waiting_customer"
    if signal.action == "retry":
        exponent = min(max(0, attempts - 1), MAX_BACKOFF_EXPONENT)
        delay = min(RETRY_BASE_SECONDS * (2 ** exponent), MAX_BACKOFF_SECONDS)
        signal.retry_at = now + timedelta(seconds=delay)
        task.review_at = signal.retry_at


def candidate_rejection(task: Task, call: OperationCall) -> str | None:
    signals = [s for s in task.recovery_signals if s.operation_id == call.operation_id]
    if not signals:
        return None
    signal = signals[-1]
    now = datetime.now(UTC)
    if signal.action == "fallback" and signal.retry_at and now < signal.retry_at:
        return "operation_cooling_down"
    return None
