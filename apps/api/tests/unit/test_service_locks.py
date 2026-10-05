"""P6 (M7): business-object locks serialize task execution across tasks."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.models.conversation import Conversation
from app.models.service_dispatch import ServiceDispatch
from app.models.service_object_lock import ServiceObjectLock
from app.models.user import User
from app.services.agent.domains.order import ORDER_GOAL, ORDER_OPERATION
from app.services.agent.intake.goals import object_key_for_task
from app.services.agent.service.contracts import Evidence, Receipt, Scope, Task
from app.services.agent.service.locks import ObjectLockStore
from app.workers.service_tasks import run_once
from tests.unit.test_service_agent import SCOPE
from tests.unit.test_service_agent import store as task_store

__all__ = ["task_store"]

CONVERSATION = "conv-1"
CUSTOMER = "customer"
ORDER_ID = "ORD202401010001"
OBJECT_KEY = "order:ORD202401010001"
LOCK_TTL_SECONDS = 30
EXPIRED_SECONDS_AGO = 1
EVIDENCE_TTL_MINUTES = 1


@pytest.mark.asyncio
async def test_acquire_conflicts_and_renews(task_store):
    locks = ObjectLockStore(task_store.sessions)
    assert (
        await locks.acquire(SCOPE, OBJECT_KEY, task_id="task-a", ttl_seconds=LOCK_TTL_SECONDS)
        is True
    )
    assert await locks.holder(SCOPE, OBJECT_KEY) == "task-a"
    assert (
        await locks.acquire(SCOPE, OBJECT_KEY, task_id="task-b", ttl_seconds=LOCK_TTL_SECONDS)
        is False
    )
    assert (
        await locks.acquire(SCOPE, OBJECT_KEY, task_id="task-a", ttl_seconds=LOCK_TTL_SECONDS)
        is True
    )
    assert await locks.holder(SCOPE, OBJECT_KEY) == "task-a"


@pytest.mark.asyncio
async def test_expired_lock_can_be_reclaimed(task_store):
    locks = ObjectLockStore(task_store.sessions)
    await locks.acquire(SCOPE, OBJECT_KEY, task_id="task-a", ttl_seconds=LOCK_TTL_SECONDS)
    async with task_store.sessions.begin() as db:
        await db.execute(
            update(ServiceObjectLock).values(
                lease_until=datetime.now(UTC) - timedelta(seconds=EXPIRED_SECONDS_AGO)
            )
        )
    assert (
        await locks.acquire(SCOPE, OBJECT_KEY, task_id="task-b", ttl_seconds=LOCK_TTL_SECONDS)
        is True
    )
    assert await locks.holder(SCOPE, OBJECT_KEY) == "task-b"


@pytest.mark.asyncio
async def test_release_is_owner_checked(task_store):
    locks = ObjectLockStore(task_store.sessions)
    await locks.acquire(SCOPE, OBJECT_KEY, task_id="task-a", ttl_seconds=LOCK_TTL_SECONDS)
    assert await locks.release(SCOPE, OBJECT_KEY, task_id="task-b") is False
    assert await locks.holder(SCOPE, OBJECT_KEY) == "task-a"
    assert await locks.release(SCOPE, OBJECT_KEY, task_id="task-a") is True
    assert await locks.holder(SCOPE, OBJECT_KEY) is None
    assert (
        await locks.acquire(SCOPE, OBJECT_KEY, task_id="task-b", ttl_seconds=LOCK_TTL_SECONDS)
        is True
    )


@pytest.mark.asyncio
async def test_locks_are_scope_isolated(task_store):
    locks = ObjectLockStore(task_store.sessions)
    await locks.acquire(SCOPE, OBJECT_KEY, task_id="task-a", ttl_seconds=LOCK_TTL_SECONDS)
    other = Scope(organization_id="other", customer_id="other")
    assert await locks.holder(other, OBJECT_KEY) is None
    assert (
        await locks.acquire(other, OBJECT_KEY, task_id="task-x", ttl_seconds=LOCK_TTL_SECONDS)
        is True
    )


def lock_task(task_id):
    return Task(
        task_id=task_id,
        scope=SCOPE,
        conversation_id=CONVERSATION,
        goal=ORDER_GOAL,
        inputs={"order_id": ORDER_ID},
        completion_condition=ORDER_GOAL,
        owner="customer_support",
    )


@pytest.mark.asyncio
async def test_locked_object_defers_dispatch_and_releases(task_store, monkeypatch):
    async with task_store.sessions.begin() as db:
        db.add(User(id=CUSTOMER, username="lockuser", email="lock@ex.com", hashed_password="x"))
        db.add(Conversation(id=CONVERSATION, user_id=CUSTOMER, status="active"))

    async def live_order(call, scope):
        return Receipt(
            status="succeeded",
            evidence=Evidence(
                operation_id=ORDER_OPERATION,
                source="scoped_order_webhook",
                data={"order_id": ORDER_ID, "customer_id": scope.customer_id, "status": "shipped"},
                expires_at=datetime.now(UTC) + timedelta(minutes=EVIDENCE_TTL_MINUTES),
            ),
        )

    monkeypatch.setattr("app.services.agent.domains.order.scoped_order", live_order)
    first, second = lock_task("lock-a"), lock_task("lock-b")
    await task_store.create(first)
    await task_store.create(second)
    async with task_store.sessions.begin() as db:
        db.add(ServiceDispatch(task_id=second.task_id, due_at=datetime.now(UTC)))

    locks = ObjectLockStore(task_store.sessions)
    key = object_key_for_task(first)
    assert (
        await locks.acquire(first.scope, key, task_id=first.task_id, ttl_seconds=LOCK_TTL_SECONDS)
        is True
    )

    counts = await run_once(sessions=task_store.sessions)
    assert counts["conflicts"] == 1
    blocked = await task_store.load(second.task_id, SCOPE)
    assert blocked.calls_used == 0

    assert await locks.release(first.scope, key, task_id=first.task_id) is True
    counts = await run_once(sessions=task_store.sessions)
    assert counts["processed"] == 1
    done = await task_store.load(second.task_id, SCOPE)
    assert done.status == "resolved"
    assert await locks.holder(SCOPE, key) is None
