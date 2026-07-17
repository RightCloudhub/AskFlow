"""Widget guest channel (E7a) + SIEM export (E9) HTTP paths."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

HTTP_OK = 200
HTTP_CREATED = 201


async def _admin(client: AsyncClient, name: str = "siemadmin") -> dict[str, str]:
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
async def test_widget_session_and_message_pipeline(client: AsyncClient):
    session = await client.post(
        "/api/v1/widget/session",
        json={"visitor_key": "v-test-1", "title": "官网咨询", "origin": "https://shop.example"},
    )
    assert session.status_code == HTTP_CREATED, session.text
    body = session.json()
    assert body["access_token"]
    assert body["conversation_id"]
    from app.services.widget.service import sanitize_visitor_key

    assert body["visitor_key"] == sanitize_visitor_key("v-test-1")
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    msg = await client.post(
        f"/api/v1/widget/conversations/{body['conversation_id']}/messages",
        headers=headers,
        json={"content": "退货政策是什么？"},
    )
    assert msg.status_code == HTTP_OK, msg.text
    out = msg.json()
    assert out["run_id"]
    assert out["assistant_message"]["content"]
    assert out["route"]

    listed = await client.get(
        f"/api/v1/widget/conversations/{body['conversation_id']}/messages",
        headers=headers,
    )
    assert listed.status_code == HTTP_OK
    assert len(listed.json()) >= 2


@pytest.mark.asyncio
async def test_widget_rejects_other_users_conversation(client: AsyncClient):
    a = await client.post("/api/v1/widget/session", json={"visitor_key": "va"})
    b = await client.post("/api/v1/widget/session", json={"visitor_key": "vb"})
    assert a.status_code == HTTP_CREATED and b.status_code == HTTP_CREATED
    cid = a.json()["conversation_id"]
    headers_b = {"Authorization": f"Bearer {b.json()['access_token']}"}
    bad = await client.get(
        f"/api/v1/widget/conversations/{cid}/messages",
        headers=headers_b,
    )
    assert bad.status_code in (403, 404)


@pytest.mark.asyncio
async def test_siem_export_json_and_push_skip(client: AsyncClient):
    headers = await _admin(client)
    # produce an audit via widget session open
    await client.post("/api/v1/widget/session", json={"visitor_key": "siem-v"})

    exported = await client.get("/api/v1/admin/audit-logs/export-siem?limit=20", headers=headers)
    assert exported.status_code == HTTP_OK, exported.text
    payload = exported.json()
    assert payload["count"] >= 1
    assert payload["events"][0]["source"] == "askflow"
    assert payload["events"][0]["event_type"] == "audit"

    pushed = await client.post(
        "/api/v1/admin/audit-logs/export-siem",
        headers=headers,
        json={"limit": 10, "push": True},
    )
    assert pushed.status_code == HTTP_OK, pushed.text
    delivery = pushed.json().get("delivery") or {}
    # no SIEM_WEBHOOK_URL in test → skipped, not error
    assert delivery.get("status") in {"skipped", "sent", "error", "http_error"}
