"""Staff handback/resolve: the conversation returns to the bot and the task settles (arch §4.9)."""

import pytest
from httpx import AsyncClient

from app.core import database
from app.models.conversation import Conversation
from app.models.service_dispatch import ServiceDispatch
from app.models.service_task import ServiceTask
from app.services.handoff.service import HandoffService

ORDER_ID = "ORD202401010001"


async def _headers(client: AsyncClient, name: str) -> dict[str, str]:
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": name, "email": f"{name}@ex.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": name, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _task_and_claimed_handoff(client: AsyncClient, name: str):
    headers = await _headers(client, name)
    me = await client.get("/api/v1/admin/auth/me", headers=headers)
    user_id = me.json()["id"]
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={"title": "hb"})
    conv_id = conv.json()["id"]
    msg = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": f"查询订单 {ORDER_ID}"},
    )
    task_id = msg.json()["assistant_message"]["meta"]["side_effects"]["service_task"]["task_id"]
    async with database.SessionLocal() as db:
        handoff = await HandoffService(db).enqueue(
            conversation_id=conv_id, user_id=user_id, summary="客户要求人工", intent="handoff"
        )
        await db.commit()
        handoff_id = handoff.id
    claim = await client.post(f"/api/v1/admin/handoffs/{handoff_id}/claim", headers=headers)
    assert claim.status_code == 200, claim.text
    async with database.SessionLocal() as db:
        row = await db.get(ServiceTask, task_id)
        version = row.version
    accept = await client.post(
        f"/api/v1/admin/service-tasks/{task_id}/accept-handoff",
        headers=headers,
        json={"expected_version": version, "handoff_id": handoff_id},
    )
    assert accept.status_code == 200, accept.text
    return headers, conv_id, task_id, handoff_id


@pytest.mark.asyncio
async def test_handback_resumes_task_and_returns_conversation(client):
    headers, conv_id, task_id, handoff_id = await _task_and_claimed_handoff(client, "hb_return")
    resp = await client.post(
        f"/api/v1/admin/handoffs/{handoff_id}/return",
        headers=headers,
        json={"note": "已电话说明"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "returned"
    async with database.SessionLocal() as db:
        checkpoint = (await db.get(ServiceTask, task_id)).checkpoint
        assert checkpoint["status"] == "active"
        assert checkpoint["owner"] == "customer_support"
        last = checkpoint["transitions"][-1]
        assert last["reason"].startswith("handback:")
        assert "已电话说明" in last["reason"]
        assert (await db.get(Conversation, conv_id)).status == "active"
        assert (await db.get(ServiceDispatch, task_id)).due_at is not None


@pytest.mark.asyncio
async def test_resolve_completes_task_and_parks_dispatch(client):
    headers, conv_id, task_id, handoff_id = await _task_and_claimed_handoff(client, "hb_resolve")
    resp = await client.post(
        f"/api/v1/admin/handoffs/{handoff_id}/resolve",
        headers=headers,
        json={"note": "已处理完成"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "resolved"
    async with database.SessionLocal() as db:
        checkpoint = (await db.get(ServiceTask, task_id)).checkpoint
        assert checkpoint["status"] == "resolved"
        assert checkpoint["transitions"][-1]["reason"].startswith("staff_resolved:")
        assert (await db.get(Conversation, conv_id)).status == "active"
        assert (await db.get(ServiceDispatch, task_id)).due_at is None


@pytest.mark.asyncio
async def test_handback_rejects_wrong_agent_and_unclaimed(client):
    headers, _conv_id, _task_id, handoff_id = await _task_and_claimed_handoff(client, "hb_guard")
    other = await _headers(client, "hb_guard_other")
    denied = await client.post(f"/api/v1/admin/handoffs/{handoff_id}/return", headers=other)
    assert denied.status_code == 403
    conv2 = await client.post("/api/v1/chat/conversations", headers=headers, json={"title": "q"})
    async with database.SessionLocal() as db:
        queued = await HandoffService(db).enqueue(
            conversation_id=conv2.json()["id"], user_id="someone", summary="q", intent="handoff"
        )
        await db.commit()
        queued_id = queued.id
    conflict = await client.post(f"/api/v1/admin/handoffs/{queued_id}/return", headers=headers)
    assert conflict.status_code == 409
