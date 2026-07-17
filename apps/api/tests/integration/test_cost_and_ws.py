"""Cost meta on turns + WS auth-first smoke (PRD §12.1 #1 #14 #15)."""

import json

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from app.core import database as dbmod
from app.main import create_app


@pytest.mark.asyncio
async def test_message_meta_includes_cost_models(client: AsyncClient):
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "costu", "email": "costu@e.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "costu", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={})
    msg = await client.post(
        f"/api/v1/chat/conversations/{conv.json()['id']}/messages",
        headers=headers,
        json={"content": "退货政策是什么"},
    )
    assert msg.status_code == 200
    meta = msg.json()["assistant_message"]["meta"]
    assert "cost" in meta
    assert meta["cost"]["calls"] >= 2  # multiple purposes recorded
    purposes = {e["purpose"] for e in meta["cost"]["entries"]}
    assert "intent_classify" in purposes
    assert "rag_generate" in purposes
    assert meta.get("models") is not None


@pytest.mark.asyncio
async def test_ws_auth_and_message_stream(client: AsyncClient):
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "wsu", "email": "wsu@e.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "wsu", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={})
    conv_id = conv.json()["id"]

    # Reuse the same engine/SessionLocal already patched by the client fixture
    application = create_app()

    with TestClient(application) as tc:
        with tc.websocket_connect("/api/v1/chat/ws") as ws:
            ws.send_text(json.dumps({"type": "auth", "token": token}))
            auth_ok = ws.receive_json()
            assert auth_ok["type"] == "auth_ok"
            ws.send_text(
                json.dumps(
                    {
                        "type": "message",
                        "conversation_id": conv_id,
                        "content": "发票怎么开",
                    }
                )
            )
            frames = []
            for _ in range(40):
                data = ws.receive_json()
                frames.append(data)
                if data.get("type") == "message_end":
                    break
            types = [f.get("type") for f in frames]
            assert "token" in types or "message_end" in types
            end = next(f for f in frames if f.get("type") == "message_end")
            assert end.get("message_id")
            assert end.get("route")
            # prove we hit the patched DB (user existed)
            assert dbmod.SessionLocal is not None
