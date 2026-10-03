"""New goals use the durable path only when enabled, without duplicate legacy effects."""

import pytest
from sqlalchemy import func, select

from app.core import database
from app.models.service_task import ServiceTask
from app.models.ticket import Ticket
from app.services.agent.memory.events import TimelineStore
from app.workers.service_tasks import run_once
from tests.integration.test_agent_runs_api import _admin
from tests.integration.test_chat_service_tasks import task_for


@pytest.mark.asyncio
async def test_ticket_takeover_runs_once_and_delivers_a_ticket_result(client, monkeypatch):
    monkeypatch.setenv("SERVICE_TASKS_GOALS", "order_status,ticket_resolution")
    headers = await _admin(client, "ticket_task_customer")
    conversation = await client.post("/api/v1/chat/conversations", headers=headers, json={})
    path = f"/api/v1/chat/conversations/{conversation.json()['id']}/messages"
    response = await client.post(path, headers=headers, json={"content": "页面一直报错"})
    assert response.status_code == 200
    effects = response.json()["assistant_message"]["meta"]["side_effects"]
    assert "service_task" in effects
    assert "ticket" not in effects
    async with database.SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Ticket)) == 0
    assert (await run_once())["processed"] == 1
    task = await task_for(effects["service_task"]["task_id"])
    assert task.status == "resolved"
    assert task.calls_used == 1
    assert (await run_once())["processed"] == 0
    async with database.SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Ticket)) == 1
    messages = (await client.get(path, headers=headers)).json()
    updates = [message for message in messages if message["meta"].get("service_task")]
    assert len(updates) == 1
    assert "工单" in updates[0]["content"]
    events = await TimelineStore(database.SessionLocal).list(
        task.scope, conversation_id=task.conversation_id
    )
    assert any(event.kind == "operation" for event in events)


@pytest.mark.asyncio
async def test_empty_allowlist_keeps_chat_on_legacy_path(client, monkeypatch):
    monkeypatch.setenv("SERVICE_TASKS_GOALS", "")
    headers = await _admin(client, "legacy_order_customer")
    conversation = await client.post("/api/v1/chat/conversations", headers=headers, json={})
    path = f"/api/v1/chat/conversations/{conversation.json()['id']}/messages"
    response = await client.post(
        path, headers=headers, json={"content": "查询订单 ORD202401019999"}
    )
    assert response.status_code == 200
    async with database.SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(ServiceTask)) == 0
