"""Chat -> durable task -> restartable worker -> one persisted assistant update."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from app.core import database
from app.models.conversation import Message
from app.models.service_dispatch import ServiceDispatch
from app.models.service_task import ServiceTask
from app.services.agent.identity import customer_scope
from app.services.agent.service.chat_order import _receipt
from app.services.agent.service.contracts import Receipt
from app.services.agent.service.dispatch import DispatchQueue
from app.services.agent.service.store import TaskStore
from app.workers.service_tasks import run_once
from tests.integration.test_agent_runs_api import _admin

ORDER_ID = "ORD202401019999"


async def create_chat_task(client):
    headers = await _admin(client, "scheduled_customer")
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={})
    conv_id = conv.json()["id"]
    path = f"/api/v1/chat/conversations/{conv_id}/messages"
    response = await client.post(path, headers=headers, json={"content": f"查询订单 {ORDER_ID}"})
    assert response.status_code == 200, response.text
    task_id = response.json()["assistant_message"]["meta"]["side_effects"]["service_task"][
        "task_id"
    ]
    return headers, conv_id, path, task_id


async def live_order(call, scope):
    return _receipt(
        call,
        scope,
        data={"order_id": ORDER_ID, "customer_id": scope.customer_id, "status": "shipped"},
    )


async def task_for(task_id):
    async with database.SessionLocal() as db:
        row = await db.get(ServiceTask, task_id)
        return await TaskStore(database.SessionLocal).load(task_id, customer_scope(row.customer_id))


@pytest.mark.asyncio
async def test_duplicate_chat_messages_share_task(client):
    headers, conv_id, path, task_id = await create_chat_task(client)
    repeated = await client.post(path, headers=headers, json={"content": f"查询订单 {ORDER_ID}"})
    info = repeated.json()["assistant_message"]["meta"]["side_effects"]["service_task"]
    assert info["task_id"] == task_id
    async with database.SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(ServiceTask)) == 1
        assert await db.scalar(select(func.count()).select_from(ServiceDispatch)) == 1


@pytest.mark.asyncio
async def test_order_result_is_delivered_once(client, monkeypatch):
    monkeypatch.setattr("app.services.agent.service.chat_order.scoped_order", live_order)
    headers, _, path, task_id = await create_chat_task(client)
    assert (await run_once())["processed"] == 1
    assert (await run_once())["processed"] == 0
    result = await task_for(task_id)
    assert result.status == "resolved" and result.calls_used == 1
    messages = (await client.get(path, headers=headers)).json()
    updates = [m for m in messages if m["meta"].get("service_task")]
    assert len(updates) == 1 and "shipped" in updates[0]["content"]


@pytest.mark.asyncio
async def test_retry_is_durable_and_cannot_run_before_due(client, monkeypatch):
    calls = []

    async def flaky(call, scope):
        calls.append(call.key)
        if len(calls) == 1:
            return Receipt(status="failed", error_kind="transient")
        return await live_order(call, scope)

    monkeypatch.setattr("app.services.agent.service.chat_order.scoped_order", flaky)
    _, _, _, task_id = await create_chat_task(client)
    await run_once()
    waiting = await task_for(task_id)
    assert waiting.status == "waiting_external"
    assert (await run_once())["processed"] == 0
    waiting.review_at = datetime.now(UTC) - timedelta(seconds=1)
    await TaskStore(database.SessionLocal).save(waiting)
    async with database.SessionLocal.begin() as db:
        await db.execute(update(ServiceDispatch).values(due_at=waiting.review_at))
    await run_once(sessions=database.SessionLocal)
    result = await task_for(task_id)
    assert result.status == "resolved" and result.calls_used == 2
    assert calls[-1].endswith(":retry")


@pytest.mark.asyncio
async def test_expired_worker_lease_can_be_reclaimed(client, monkeypatch):
    monkeypatch.setattr("app.services.agent.service.chat_order.scoped_order", live_order)
    _, _, _, task_id = await create_chat_task(client)
    claimed = await DispatchQueue(database.SessionLocal).claim(task_id)
    assert claimed is not None
    assert (await run_once())["processed"] == 0
    async with database.SessionLocal.begin() as db:
        await db.execute(
            update(ServiceDispatch).values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
        )
    assert (await run_once())["processed"] == 1
    assert (await task_for(task_id)).status == "resolved"


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal", ["closed_unresolved", "handed_off"])
async def test_cancelled_or_handed_off_task_never_executes(client, monkeypatch, terminal):
    calls = []

    async def must_not_run(call, scope):
        calls.append(call)
        return await live_order(call, scope)

    monkeypatch.setattr("app.services.agent.service.chat_order.scoped_order", must_not_run)
    _, _, _, task_id = await create_chat_task(client)
    task = await task_for(task_id)
    task.status = terminal
    await TaskStore(database.SessionLocal).save(task)
    await run_once()
    assert calls == []
    assert (await task_for(task_id)).status == terminal


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["wrong_customer", "mock"])
async def test_unverified_result_does_not_resolve_or_leak(client, monkeypatch, invalid):
    async def invalid_order(call, scope):
        return _receipt(
            call,
            scope,
            data={
                "order_id": ORDER_ID,
                "customer_id": "other-customer",
                "status": "mock" if invalid == "mock" else "private-status",
            },
        )

    monkeypatch.setattr("app.services.agent.service.chat_order.scoped_order", invalid_order)
    headers, _, path, task_id = await create_chat_task(client)
    await run_once()
    assert (await task_for(task_id)).status == "waiting_external"
    assert "private-status" not in (await client.get(path, headers=headers)).text


@pytest.mark.asyncio
async def test_chat_failure_rolls_back_task_and_dispatch(client, monkeypatch):
    headers = await _admin(client, "rollback_customer")
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={})

    def fail_meta(_result):
        raise RuntimeError("response persistence failed")

    monkeypatch.setattr(
        "app.services.chat.session.turn.ChatTurn._response_meta", staticmethod(fail_meta)
    )
    with pytest.raises(RuntimeError):
        await client.post(
            f"/api/v1/chat/conversations/{conv.json()['id']}/messages",
            headers=headers,
            json={"content": f"查询订单 {ORDER_ID}"},
        )
    async with database.SessionLocal() as db:
        for model in [ServiceTask, ServiceDispatch, Message]:
            assert await db.scalar(select(func.count()).select_from(model)) == 0
