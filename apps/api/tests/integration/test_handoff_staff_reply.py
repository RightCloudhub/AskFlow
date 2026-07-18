"""Staff reply + messages on claimed handoff (PRD §4.7)."""

import pytest
from httpx import AsyncClient

HTTP_OK = 200


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


async def _enqueue_handoff(client: AsyncClient, headers: dict[str, str]) -> str:
    conv = await client.post(
        "/api/v1/chat/conversations", headers=headers, json={"title": "h"}
    )
    conv_id = conv.json()["id"]
    msg = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "请转人工客服处理"},
    )
    assert msg.status_code == HTTP_OK, msg.text
    assert msg.json()["route"] == "handoff"
    queue = await client.get("/api/v1/admin/handoffs", headers=headers)
    assert queue.status_code == HTTP_OK
    assert len(queue.json()) >= 1
    return queue.json()[0]["id"]


@pytest.mark.asyncio
async def test_staff_reply_and_list_messages(client: AsyncClient):
    headers = await _headers(client, "staffreply_user")
    hid = await _enqueue_handoff(client, headers)

    claim = await client.post(f"/api/v1/admin/handoffs/{hid}/claim", headers=headers)
    assert claim.status_code == HTTP_OK

    hist = await client.get(f"/api/v1/admin/handoffs/{hid}/messages", headers=headers)
    assert hist.status_code == HTTP_OK
    assert any(m["role"] == "user" for m in hist.json())

    reply = await client.post(
        f"/api/v1/admin/handoffs/{hid}/reply",
        headers=headers,
        json={"content": "您好，我是人工客服"},
    )
    assert reply.status_code == HTTP_OK, reply.text
    body = reply.json()
    assert body["role"] == "staff"
    assert "人工客服" in body["content"]

    hist2 = await client.get(f"/api/v1/admin/handoffs/{hid}/messages", headers=headers)
    assert any(m["role"] == "staff" for m in hist2.json())
