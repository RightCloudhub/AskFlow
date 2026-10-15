"""Confirmation and approval gates: park the task instead of calling the external system."""

from datetime import UTC, datetime, timedelta

from app.services.agent.gateway.confirmation import issue_confirmation
from app.services.agent.gateway.ledger import STATUS_NEEDS_CONFIRMATION
from app.services.agent.service.contracts import PendingConfirmation, Receipt, RecoverySignal
from app.services.outbox.store import EVENT_CONFIRMATION_REQUESTED, emit

APPROVAL_REVIEW_SECONDS = 60
CONFIRMATION_PROMPT = "有一项操作需要您的确认（{capability}）。请回复「确认」以继续。"


class ParkFlow:
    """Mixin: relies on ``self.store`` and ``self.gateway``."""

    async def _park_for_confirmation(
        self, *, task, call, spec, ctx, decision
    ) -> Receipt:
        async with self.store.sessions.begin() as db:
            token = await issue_confirmation(
                db, scope_id=task.task_id, step=call.key, args=call.arguments, task_id=task.task_id
            )
            await self.gateway.record_decision(
                capability=spec,
                args=call.arguments,
                ctx=ctx,
                decision=decision,
                status=STATUS_NEEDS_CONFIRMATION,
                db=db,
            )
            if task.conversation_id:
                await emit(
                    db,
                    aggregate="task",
                    aggregate_id=task.task_id,
                    event_type=EVENT_CONFIRMATION_REQUESTED,
                    payload={
                        "conversation_id": task.conversation_id,
                        "task_id": task.task_id,
                        "capability": spec.name,
                        "content": CONFIRMATION_PROMPT.format(capability=spec.name),
                    },
                )
        task.pending_confirmation = PendingConfirmation(
            capability=spec.name,
            step=call.key,
            args_hash=token.args_hash,
            nonce=token.nonce,
            token=token.token,
            expires_at=token.expires_at,
        )
        task.recovery_signals.append(
            RecoverySignal(
                operation_id=call.operation_id,
                request_key=call.key,
                kind="invalid_input",
                action="ask_customer",
            )
        )
        task.status, task.wake_condition = "waiting_customer", f"confirm:{token.nonce}"
        task.review_at = token.expires_at
        await self.store.save(task)
        return Receipt(status="failed", error_kind="invalid_input", error="confirmation_required")

    async def _park_for_approval(self, *, task, call, spec, ctx, decision) -> Receipt:
        await self.gateway.record_decision(
            capability=spec,
            args=call.arguments,
            ctx=ctx,
            decision=decision,
            status=STATUS_NEEDS_CONFIRMATION,
            error={"reasons": list(decision.reasons)},
        )
        task.recovery_signals.append(
            RecoverySignal(
                operation_id=call.operation_id,
                request_key=call.key,
                kind="permission",
                action="owner_review",
            )
        )
        task.status, task.wake_condition = "waiting_external", "owner_review:human_approval"
        task.review_at = datetime.now(UTC) + timedelta(seconds=APPROVAL_REVIEW_SECONDS)
        await self.store.save(task)
        return Receipt(status="failed", error_kind="permission", error="human_approval_required")
