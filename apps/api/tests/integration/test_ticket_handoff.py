"""Ticket dedupe + handoff claim 409 + timeout (PRD §12.1 #6 #7)."""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import database as dbmod
from app.schemas.ticket import TicketCreate
from app.services.ticket.repository.service import TicketRepository


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


@pytest.mark.asyncio
async def test_ticket_open_dedupe_via_api(client: AsyncClient):
    headers = await _headers(client, "ticketuser")
    payload = {"title": "无法登录系统", "description": "desc", "type": "fault_report", "priority": "high"}
    r1 = await client.post("/api/v1/tickets", headers=headers, json=payload)
    r2 = await client.post("/api/v1/tickets", headers=headers, json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_ticket_concurrent_create_or_get(client: AsyncClient):
    # drive repository path: sequential races still converge; parallel best-effort
    headers = await _headers(client, "concuser")
    me = await client.get("/api/v1/admin/auth/me", headers=headers)
    user_id = me.json()["id"]

    session_factory = async_sessionmaker(dbmod.engine, class_=AsyncSession, expire_on_commit=False)

    async def create_once():
        async with session_factory() as session:
            repo = TicketRepository(session)
            t, _ = await repo.create_or_get_open(
                user_id,
                TicketCreate(title="并发工单标题", description="x", type="fault_report"),
            )
            await session.commit()
            return t.id

    # first create, then concurrent attempts that must all return same id
    first = await create_once()
    ids = await asyncio.gather(create_once(), create_once(), create_once())
    assert set(ids) == {first}


@pytest.mark.asyncio
async def test_handoff_claim_409_and_timeout(client: AsyncClient):
    h_user = await _headers(client, "handuser")
    h_agent1 = await _headers(client, "agentone")  # second user is not admin unless first — first was handuser as admin
    # create agent-like second claimer: promote via another register after admin exists → user role
    # use admin (handuser) for claim APIs; second claimer needs agent/admin — register agenttwo then reuse admin for first claim

    # user conversation → handoff
    conv = await client.post("/api/v1/chat/conversations", headers=h_user, json={"title": "h"})
    conv_id = conv.json()["id"]
    msg = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=h_user,
        json={"content": "请转人工客服处理"},
    )
    assert msg.status_code == 200, msg.text
    assert msg.json()["route"] == "handoff"

    queue = await client.get("/api/v1/admin/handoffs", headers=h_user)
    assert queue.status_code == 200
    assert len(queue.json()) >= 1
    hid = queue.json()[0]["id"]

    c1 = await client.post(f"/api/v1/admin/handoffs/{hid}/claim", headers=h_user)
    assert c1.status_code == 200
    # same agent re-claim ok
    c1b = await client.post(f"/api/v1/admin/handoffs/{hid}/claim", headers=h_user)
    assert c1b.status_code == 200

    # different agent should 409 — need another admin/agent. Create via direct role not available;
    # use agentone token after elevating: second registered user is role=user → 403.
    # Force expire path instead for timeout, and simulate 409 by claiming with another user who we promote through system:
    # Re-register not possible. Directly call service with different agent_id is better for 409.

    from app.services.handoff.service import HandoffService

    session_factory = async_sessionmaker(dbmod.engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        svc = HandoffService(session)
        with pytest.raises(Exception) as ei:
            await svc.claim(hid, "other-agent-id")
        # FastAPI HTTPException 409
        assert getattr(ei.value, "status_code", None) == 409
        await session.rollback()

    # timeout sweep via force-expire admin endpoint
    swept = await client.post("/api/v1/admin/system/handoff-sweep/force-expire", headers=h_user)
    # handoff already claimed — force expire only queues; create a fresh queued handoff
    conv2 = await client.post("/api/v1/chat/conversations", headers=h_user, json={"title": "h2"})
    # return first and create new? or enqueue on new conversation
    # mark conversation active and handoff again on new conv
    msg2 = await client.post(
        f"/api/v1/chat/conversations/{conv2.json()['id']}/messages",
        headers=h_user,
        json={"content": "找真人客服转人工"},
    )
    assert msg2.json()["route"] == "handoff"
    swept = await client.post("/api/v1/admin/system/handoff-sweep/force-expire", headers=h_user)
    assert swept.status_code == 200, swept.text
    assert swept.json()["swept"] >= 1
    outcomes = swept.json()["outcomes"]
    assert outcomes[0]["ticket_id"]

    tickets = await client.get("/api/v1/tickets", headers=h_user)
    types = {t["type"] for t in tickets.json()}
    assert "handoff_timeout" in types
