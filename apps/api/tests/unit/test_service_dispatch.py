"""Lease races, finite fault recovery, delivery fencing and scoped HTTP contracts."""

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select, update

from app.core.config import get_settings
from app.models.conversation import Conversation, Message
from app.models.service_dispatch import ServiceDispatch
from app.services.agent.service.chat_order import scoped_order
from app.services.agent.service.delivery import finish_dispatch
from app.services.agent.service.dispatch import DispatchQueue
from app.workers.service_tasks import run_once
from tests.unit.test_service_agent import SCOPE, call, store, success, task

__all__ = ["store"]


async def enqueue(store, task_id):
    async with store.sessions.begin() as db:
        db.add(ServiceDispatch(task_id=task_id, due_at=datetime.now(UTC)))


@pytest.mark.asyncio
async def test_two_workers_only_one_claims_due_task(store):
    await enqueue(store, "job")
    queue = DispatchQueue(store.sessions)
    results = await asyncio.gather(queue.claim("job"), DispatchQueue(store.sessions).claim("job"))
    assert sum(result is not None for result in results) == 1
    assert await queue.due() == []


@pytest.mark.asyncio
async def test_orphan_job_stops_after_finite_failures(store):
    await enqueue(store, "missing-task")
    for _ in range(3):
        async with store.sessions.begin() as db:
            await db.execute(update(ServiceDispatch).values(due_at=datetime.now(UTC)))
        assert (await run_once(sessions=store.sessions))["failed"] == 1
    async with store.sessions() as db:
        job = await db.get(ServiceDispatch, "missing-task")
        assert job.due_at is None and job.last_error == "dispatch_failure"
        assert job.attempts == 3


@pytest.mark.asyncio
async def test_dispatch_failures_leave_valid_task_owned(store, monkeypatch):
    original = task()
    await store.create(original)
    await enqueue(store, original.task_id)
    async def broken(_store, _claim):
        raise RuntimeError("worker failed")
    monkeypatch.setattr("app.workers.service_tasks.dispatch_one", broken)
    for _ in range(3):
        async with store.sessions.begin() as db:
            await db.execute(update(ServiceDispatch).values(due_at=datetime.now(UTC)))
        await run_once(sessions=store.sessions)
    result = await store.load(original.task_id, SCOPE)
    assert result.status == "waiting_external"
    assert result.wake_condition == "owner_review:dispatch_failure"
    assert result.recovery_signals[-1].operation_id == "scheduler"


@pytest.mark.asyncio
async def test_one_claim_failure_does_not_block_other_jobs(store, monkeypatch):
    await enqueue(store, "bad")
    await enqueue(store, "good")
    original_claim = DispatchQueue.claim
    async def claim(queue, task_id):
        if task_id == "bad":
            raise RuntimeError("broken claim")
        return await original_claim(queue, task_id)
    called = []
    async def dispatch(_store, claim):
        called.append(claim.task_id)
    monkeypatch.setattr(DispatchQueue, "claim", claim)
    monkeypatch.setattr("app.workers.service_tasks.dispatch_one", dispatch)
    counts = await run_once(sessions=store.sessions)
    assert counts["processed"] == 1 and counts["failed"] == 1
    assert called == ["good"]


@pytest.mark.asyncio
async def test_old_lease_cannot_finish_reclaimed_job(store):
    original = task()
    await store.create(original)
    await enqueue(store, original.task_id)
    queue = DispatchQueue(store.sessions)
    first = await queue.claim(original.task_id)
    async with store.sessions.begin() as db:
        await db.execute(update(ServiceDispatch).values(
            lease_until=datetime.now(UTC) - timedelta(seconds=1)))
    second = await queue.claim(original.task_id)
    await finish_dispatch(store, first, original)
    async with store.sessions() as db:
        assert (await db.get(ServiceDispatch, original.task_id)).lease_token == second.token


@pytest.mark.asyncio
async def test_cancel_after_execution_fences_stale_chat_delivery(store):
    original = task()
    original.conversation_id = "conversation"
    original.status = "resolved"
    original.evidence = [(await success(call())).evidence]
    await store.create(original)
    await enqueue(store, original.task_id)
    claim = await DispatchQueue(store.sessions).claim(original.task_id)
    newer = await store.load(original.task_id, SCOPE)
    newer.status = "closed_unresolved"
    await store.save(newer)
    await finish_dispatch(store, claim, original)
    async with store.sessions() as db:
        assert list(await db.scalars(select(Message))) == []
        assert (await db.get(ServiceDispatch, original.task_id)).due_at is not None


@pytest.mark.asyncio
async def test_repeated_delivery_is_idempotent(store):
    original = task()
    original.conversation_id = "conversation"
    original.status = "resolved"
    original.evidence = [(await success(call())).evidence]
    async with store.sessions.begin() as db:
        db.add(Conversation(id="conversation", user_id=SCOPE.customer_id, status="active"))
    await store.create(original)
    await enqueue(store, original.task_id)
    claim = await DispatchQueue(store.sessions).claim(original.task_id)
    await finish_dispatch(store, claim, original)
    await finish_dispatch(store, claim, original)
    async with store.sessions() as db:
        assert len(list(await db.scalars(select(Message)))) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("result", ["ok", "wrong_customer", "wrong_order", "mock", "forbidden", "retry"])
async def test_scoped_http_contract(monkeypatch, result):
    settings = get_settings()
    monkeypatch.setattr(settings, "order_lookup_url", "https://orders.test/status")
    monkeypatch.setattr(settings, "order_lookup_token", "test-token")
    async def handler(request):
        assert request.url.params["customer_id"] == SCOPE.customer_id
        assert request.headers["Authorization"] == "Bearer test-token"
        status = {"forbidden": 403, "retry": 503}.get(result, 200)
        return httpx.Response(status, json={
            "order_id": "other" if result == "wrong_order" else "owned",
            "customer_id": "other" if result == "wrong_customer" else SCOPE.customer_id,
            "status": "mock" if result == "mock" else "shipped",
        })
    client_class = httpx.AsyncClient
    monkeypatch.setattr("app.services.agent.service.chat_order.httpx.AsyncClient",
                        lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs))
    receipt = await scoped_order(call(), SCOPE)
    assert (receipt.status == "succeeded") is (result == "ok")
    if result == "retry":
        assert receipt.error_kind == "transient"
    if result == "forbidden":
        assert receipt.error_kind == "permission"
