"""Enterprise admin APIs: connectors, launch cards, costs, users, SLA, MCP, SSO."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import database as dbmod
from app.models.enums import TicketPriority, TicketStatus
from app.models.ticket import Ticket
from app.services.auth.oidc import encode_mock_id_token
from datetime import UTC, datetime, timedelta


async def _admin(client: AsyncClient, name: str = "entadmin") -> dict[str, str]:
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
async def test_connectors_two_defaults_and_invoke(client: AsyncClient):
    headers = await _admin(client, "connadmin")
    listed = await client.get("/api/v1/admin/connectors", headers=headers)
    assert listed.status_code == 200
    names = {c["name"] for c in listed.json()}
    assert "order_status" in names
    assert "crm_lookup" in names

    inv = await client.post(
        "/api/v1/admin/connectors/order_status/invoke",
        headers=headers,
        json={"params": {"order_id": "1"}},
    )
    assert inv.status_code == 200
    body = inv.json()
    assert body.get("connector") == "order_status"
    # ok or mock degradation — never bare error without mock data_source
    assert body.get("status") in {"ok", "mock"}, body
    assert body.get("data_source") in {"connector", "mock"}
    if body["status"] == "mock":
        assert body.get("data", {}).get("mock") is True


@pytest.mark.asyncio
async def test_launch_card_and_costs_and_mcp(client: AsyncClient):
    headers = await _admin(client, "lcadmin")
    # chat turn to generate cost rows
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={})
    await client.post(
        f"/api/v1/chat/conversations/{conv.json()['id']}/messages",
        headers=headers,
        json={"content": "退货政策是什么"},
    )
    costs = await client.get("/api/v1/admin/costs/summary", headers=headers)
    assert costs.status_code == 200
    assert "by_purpose" in costs.json()

    card = await client.post(
        "/api/v1/admin/launch-cards",
        headers=headers,
        json={
            "title": "RAG threshold tweak",
            "change_summary": "raise grounding",
            "expected_metrics": {"faq_resolve_rate": 0.7},
        },
    )
    assert card.status_code == 200
    cid = card.json()["id"]
    measured = await client.post(
        f"/api/v1/admin/launch-cards/{cid}/measure",
        headers=headers,
        json={"measured_metrics": {"faq_resolve_rate": 0.72}},
    )
    assert measured.status_code == 200
    assert measured.json()["status"] == "measured"
    assert measured.json()["measured_metrics"]["faq_resolve_rate"] == 0.72

    # MCP sync with enabled flag via env not set — empty register ok
    mcp = await client.post("/api/v1/admin/mcp/sync", headers=headers)
    assert mcp.status_code == 200


@pytest.mark.asyncio
async def test_sso_login_and_user_export_delete(client: AsyncClient):
    headers = await _admin(client, "useradmin")
    # create second user via register
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "victim", "email": "victim@ex.com", "password": "password123"},
    )
    users = await client.get("/api/v1/admin/users", headers=headers)
    assert users.status_code == 200
    victim = next(u for u in users.json() if u["username"] == "victim")

    exp = await client.get(f"/api/v1/admin/users/{victim['id']}/export", headers=headers)
    assert exp.status_code == 200
    assert exp.json()["user"]["email"] == "victim@ex.com"

    dis = await client.patch(
        f"/api/v1/admin/users/{victim['id']}/active",
        headers=headers,
        json={"is_active": False},
    )
    assert dis.status_code == 200
    assert dis.json()["is_active"] is False

    # SSO path
    id_token = encode_mock_id_token(
        {
            "sub": "sso-9",
            "email": "sso9@corp.com",
            "preferred_username": "sso9",
            "roles": ["admin"],
        }
    )
    sso = await client.post("/api/v1/admin/sso/oidc/login", json={"id_token": id_token})
    assert sso.status_code == 200
    assert sso.json()["access_token"]
    assert sso.json()["user"]["role"] == "admin"

    # delete data
    deleted = await client.delete(
        f"/api/v1/admin/users/{victim['id']}/data", headers=headers
    )
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True


@pytest.mark.asyncio
async def test_sla_scan_api_and_out_of_scope_chat(client: AsyncClient):
    headers = await _admin(client, "slaadmin")
    # create ticket then backdate via ORM
    me = await client.get("/api/v1/admin/auth/me", headers=headers)
    uid = me.json()["id"]
    t = await client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"title": "SLA urgent", "description": "d", "priority": "urgent"},
    )
    tid = t.json()["id"]

    factory = async_sessionmaker(dbmod.engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        ticket = await session.get(Ticket, tid)
        ticket.created_at = datetime.now(UTC) - timedelta(minutes=30)
        ticket.priority = TicketPriority.URGENT.value
        ticket.status = TicketStatus.PENDING.value
        ticket.sla_state = "ok"
        await session.commit()

    from app.services.notify.service import clear_notify_sink, get_notify_sink

    clear_notify_sink()
    scan = await client.post("/api/v1/admin/sla/scan", headers=headers)
    assert scan.status_code == 200
    assert scan.json()["scanned_changes"] >= 1
    sink = get_notify_sink()
    assert any(e["event"].startswith("sla.") for e in sink)

    # out_of_scope chat
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={})
    msg = await client.post(
        f"/api/v1/chat/conversations/{conv.json()['id']}/messages",
        headers=headers,
        json={"content": "请给我癌症治疗方案和处方建议"},
    )
    assert msg.status_code == 200
    assert msg.json()["route"] == "refuse"
    assert msg.json()["intent"] == "out_of_scope"
    assert "根据知识库资料" not in msg.json()["assistant_message"]["content"]
