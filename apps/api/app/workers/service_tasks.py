"""Restart-safe scheduling for chat-created service tasks."""

import asyncio
import logging
from datetime import UTC, datetime

from app.core import database
from app.models.service_task import ServiceTask
from app.services.agent.intake.goals import object_key_for_task
from app.services.agent.memory.events import TimelineStore
from app.services.agent.service.contracts import RecoverySignal, Scope
from app.services.agent.service.delivery import finish_dispatch
from app.services.agent.service.dispatch import MAX_DISPATCH_FAILURES, DispatchQueue
from app.services.agent.service.driver import advance
from app.services.agent.service.lifecycle import VerifiedWakeup, wake_task
from app.services.agent.service.locks import ObjectLockStore
from app.services.agent.service.policies import default_policy_registry
from app.services.agent.service.settings import ServiceSettings
from app.services.agent.service.store import TaskConflict, TaskStore

DISPATCH_TIMEOUT_SECONDS = 240
OBJECT_LOCK_TTL_SECONDS = 300
logger = logging.getLogger(__name__)


async def _load(store, task_id):
    async with store.sessions() as db:
        row = await db.get(ServiceTask, task_id)
        if row is None:
            raise LookupError("Dispatch task missing")
        scope = Scope(organization_id=row.organization_id, customer_id=row.customer_id)
    return await store.load(task_id, scope)


async def dispatch_one(store, claim):
    task = await _load(store, claim.task_id)
    if task.status in {"resolved", "closed_unresolved", "handed_off"}:
        return await finish_dispatch(store, claim, task)
    builder = default_policy_registry().resolve(task.completion_condition)
    if claim.attempts > MAX_DISPATCH_FAILURES or builder is None:
        reason = "unknown_goal" if builder is None else "dispatch_failure"
        task.status, task.wake_condition = "waiting_external", f"owner_review:{reason}"
        task.review_at = datetime.now(UTC)
        await store.save(task)
        return await finish_dispatch(store, claim, task)
    if task.status == "waiting_external" and (task.wake_condition or "").startswith("retry:"):
        await wake_task(
            store,
            VerifiedWakeup(task_id=task.task_id, scope=task.scope, condition=task.wake_condition),
        )
    result = await _advance_locked(store, task, builder=builder)
    await TimelineStore(store.sessions).append(result)
    await finish_dispatch(store, claim, result)


async def _advance_locked(store, task, *, builder):
    key = object_key_for_task(task)
    if key is None:
        return await advance(builder(store, task), task.task_id, scope=task.scope)
    locks = ObjectLockStore(store.sessions)
    acquired = await locks.acquire(
        task.scope, key, task_id=task.task_id, ttl_seconds=OBJECT_LOCK_TTL_SECONDS
    )
    if not acquired:
        raise TaskConflict("Business object is held by another task")
    try:
        return await advance(builder(store, task), task.task_id, scope=task.scope)
    finally:
        await locks.release(task.scope, key, task_id=task.task_id)


async def run_once(*, sessions=None) -> dict[str, int]:
    store = TaskStore(sessions or database.SessionLocal)
    queue = DispatchQueue(store.sessions)
    counts = {"processed": 0, "failed": 0, "conflicts": 0}
    for task_id in await queue.due():
        try:
            outcome = await _run_claim(store, queue, task_id)
        except Exception as exc:
            outcome = "failed"
            logger.warning("Service dispatch storage failed (%s)", type(exc).__name__)
        if outcome:
            counts[outcome] += 1
    return counts


async def _run_claim(store, queue, task_id):
    claim = await queue.claim(task_id)
    if claim is None:
        return None
    try:
        await asyncio.wait_for(dispatch_one(store, claim), timeout=DISPATCH_TIMEOUT_SECONDS)
        return "processed"
    except TaskConflict:
        await queue.reschedule(claim)
        return "conflicts"
    except Exception as exc:
        logger.warning("Service dispatch failed (%s); lease permits recovery", type(exc).__name__)
        await _recover_failure(store, queue, claim)
        return "failed"


async def _recover_failure(store, queue, claim):
    if claim.attempts >= MAX_DISPATCH_FAILURES:
        try:
            task = await _load(store, claim.task_id)
            if task.status not in {"resolved", "closed_unresolved", "handed_off"}:
                task.status, task.wake_condition = (
                    "waiting_external",
                    "owner_review:dispatch_failure",
                )
                task.review_at = datetime.now(UTC)
                task.recovery_signals.append(
                    RecoverySignal(
                        operation_id="scheduler",
                        request_key=claim.token,
                        kind="permanent",
                        action="owner_review",
                    )
                )
                await store.save(task)
            await finish_dispatch(store, claim, task)
            return
        except TaskConflict:
            return await queue.reschedule(claim)
        except Exception as exc:
            logger.warning("Dispatch requires operator repair (%s)", type(exc).__name__)
    await queue.record_failure(claim)


async def periodic_loop():
    settings = ServiceSettings()
    while True:
        try:
            await run_once()
        except Exception as exc:
            logger.warning("Service task scan failed (%s)", type(exc).__name__)
        await asyncio.sleep(settings.poll_seconds)
