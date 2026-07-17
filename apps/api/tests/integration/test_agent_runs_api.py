"""HTTP path: admin agent-runs list/detail after chat turn persists run."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

HTTP_OK = 200
HTTP_CREATED = 201
OK_STATUSES = (HTTP_OK, HTTP_CREATED)


async def _admin(client: AsyncClient, name: str = "runadmin") -> dict[str, str]:
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": name, "email": f"{name}@ex.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": name, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _chat_turn(client: AsyncClient, headers: dict[str, str]) -> str:
    conv = await client.post(
        "/api/v1/chat/conversations",
        headers=headers,
        json={"title": "run-replay"},
    )
    assert conv.status_code in OK_STATUSES, conv.text
    msg = await client.post(
        f"/api/v1/chat/conversations/{conv.json()['id']}/messages",
        headers=headers,
        json={"content": "你好，退货政策是什么？"},
    )
    assert msg.status_code in OK_STATUSES, msg.text
    run_id = msg.json().get("run_id")
    assert run_id, msg.json()
    return run_id


@pytest.mark.asyncio
async def test_agent_run_replay_via_admin_api(client: AsyncClient):
    headers = await _admin(client)
    run_id = await _chat_turn(client, headers)

    listed = await client.get("/api/v1/admin/agent-runs?limit=20", headers=headers)
    assert listed.status_code == HTTP_OK, listed.text
    assert any(r["run_id"] == run_id for r in listed.json())

    detail = await client.get(f"/api/v1/admin/agent-runs/{run_id}", headers=headers)
    assert detail.status_code == HTTP_OK, detail.text
    d = detail.json()
    assert d["run_id"] == run_id
    assert len(d["steps"]) >= 1 and d["steps"][0]["kind"] == "route"
    assert "cost" in d and "estimated_usd" in d["cost"]


@pytest.mark.asyncio
async def test_notify_test_emit_and_sla_status(client: AsyncClient):
    headers = await _admin(client, "notifyadmin")
    emit = await client.post(
        "/api/v1/admin/notify/test-emit",
        headers=headers,
        json={"event": "pilot.test", "payload": {"k": 1}},
    )
    assert emit.status_code == HTTP_OK and emit.json().get("ok") is True
    assert emit.json().get("signature")

    logs = await client.get("/api/v1/admin/notify/logs?limit=5", headers=headers)
    assert logs.status_code == HTTP_OK and isinstance(logs.json(), list)

    status = await client.get("/api/v1/admin/sla/status", headers=headers)
    assert status.status_code == HTTP_OK
    body = status.json()
    assert "counts" in body and "tickets" in body
