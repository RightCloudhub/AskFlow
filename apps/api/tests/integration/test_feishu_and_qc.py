"""HTTP: Feishu webhook + QC admin APIs."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

HTTP_OK = 200
HTTP_CREATED = 201


async def _admin(client: AsyncClient, name: str = "qcadm") -> dict[str, str]:
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": name, "email": f"{name}@ex.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": name, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_feishu_challenge_and_message(client: AsyncClient):
    ch = await client.post(
        "/api/v1/channels/feishu/events",
        json={"type": "url_verification", "challenge": "ping-xyz", "token": "any"},
    )
    assert ch.status_code == HTTP_OK
    assert ch.json().get("challenge") == "ping-xyz"

    msg = await client.post(
        "/api/v1/channels/feishu/events",
        json={
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "sender": {"sender_id": {"open_id": "ou_http_1"}},
                "message": {
                    "message_id": "om_http",
                    "chat_id": "oc_http",
                    "message_type": "text",
                    "content": json.dumps({"text": "退货政策是什么？"}),
                },
            },
        },
    )
    assert msg.status_code == HTTP_OK, msg.text
    body = msg.json()
    assert body.get("code") == 0
    assert body.get("run_id")
    assert body.get("reply_text")


@pytest.mark.asyncio
async def test_qc_summary_and_low_quality(client: AsyncClient):
    headers = await _admin(client)
    # produce a run via chat
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=headers,
        json={"title": "qc"},
    )
    assert conv.status_code in (HTTP_OK, HTTP_CREATED)
    await client.post(
        f"/api/v1/chat/conversations/{conv.json()['id']}/messages",
        headers=headers,
        json={"content": "如何重置密码？"},
    )

    summary = await client.get("/api/v1/admin/qc/summary", headers=headers)
    assert summary.status_code == HTTP_OK, summary.text
    data = summary.json()
    assert "agent_runs" in data
    assert "refuse_rate" in data
    assert "thumbs_down_rate" in data

    low = await client.get("/api/v1/admin/qc/low-quality?limit=20", headers=headers)
    assert low.status_code == HTTP_OK
    assert "runs" in low.json()
