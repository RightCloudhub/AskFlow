"""Auth + chat happy path integration."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_chat(client: AsyncClient):
    reg = await client.post(
        "/api/v1/admin/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
        },
    )
    assert reg.status_code == 201, reg.text
    body = reg.json()
    assert body["username"] == "alice"
    # first account bootstraps as admin for ops access
    assert body["role"] in {"user", "admin"}

    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "alice", "password": "password123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/admin/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "alice"

    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=headers,
        json={"title": "测试会话"},
    )
    assert conv.status_code == 201
    conv_id = conv.json()["id"]

    msg = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "退货政策是什么？"},
    )
    assert msg.status_code == 200, msg.text
    data = msg.json()
    assert data["route"] in {"rag", "clarify", "blocked"}
    assert data["assistant_message"]["content"]

    # health
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] in {"ok", "degraded"}


@pytest.mark.asyncio
async def test_bad_password(client: AsyncClient):
    await client.post(
        "/api/v1/admin/auth/register",
        json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "password123",
        },
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "bob", "password": "wrong-password"},
    )
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_order_slot_and_tool(client: AsyncClient):
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "carol", "email": "carol@example.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "carol", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={})
    conv_id = conv.json()["id"]

    r1 = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "查一下我的订单物流"},
    )
    assert r1.status_code == 200
    assert r1.json()["route"] == "tool"
    assert "订单号" in r1.json()["assistant_message"]["content"]

    r2 = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "ORD202401019999"},
    )
    assert r2.status_code == 200
    assert "ORD202401019999" in r2.json()["assistant_message"]["content"]


@pytest.mark.asyncio
async def test_classify_and_rag(client: AsyncClient):
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "dave", "email": "dave@example.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "dave", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    c = await client.post(
        "/api/v1/agent/classify",
        headers=headers,
        json={"text": "转人工客服"},
    )
    assert c.status_code == 200
    assert c.json()["intent"] == "handoff"
    assert c.json()["route"] == "handoff"

    rag = await client.post(
        "/api/v1/rag/query",
        headers=headers,
        json={"question": "如何申请发票"},
    )
    assert rag.status_code == 200
    body = rag.json()
    assert "answer" in body
