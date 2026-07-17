"""Skill-team scoped handoff inbox (PRD §12.2 criterion 2)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import database as dbmod
from app.core.security import hash_password
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus, HandoffStatus, UserRole
from app.models.handoff import HandoffSession
from app.models.user import User
from app.services.handoff.service import HandoffService
from app.services.team.service import TeamService


async def _register_login(client: AsyncClient, name: str, *, first_admin: bool = False) -> tuple[dict, str]:
    """Return (headers, user_id). First call may bootstrap admin."""
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": name, "email": f"{name}@ex.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": name, "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/admin/auth/me", headers=headers)
    return headers, me.json()["id"]


@pytest.mark.asyncio
async def test_agent_sees_only_team_scoped_handoffs(client: AsyncClient):
    admin_h, admin_id = await _register_login(client, "scope_admin")
    # promote nothing — first user is admin

    # Create two agents via register (role=user) then elevate via DB to agent
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "agent_fault", "email": "af@ex.com", "password": "password123"},
    )
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "agent_order", "email": "ao@ex.com", "password": "password123"},
    )
    login_f = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "agent_fault", "password": "password123"},
    )
    login_o = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "agent_order", "password": "password123"},
    )
    h_fault = {"Authorization": f"Bearer {login_f.json()['access_token']}"}
    h_order = {"Authorization": f"Bearer {login_o.json()['access_token']}"}
    me_f = await client.get("/api/v1/admin/auth/me", headers=h_fault)
    me_o = await client.get("/api/v1/admin/auth/me", headers=h_order)
    fault_id = me_f.json()["id"]
    order_id = me_o.json()["id"]

    factory = async_sessionmaker(dbmod.engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        for uid in (fault_id, order_id):
            u = await db.get(User, uid)
            u.role = UserRole.AGENT.value
        # teams
        ts = TeamService(db)
        t_fault = await ts.create_team("fault-team", intent_scope="fault_report,complaint,handoff")
        t_order = await ts.create_team("order-team", intent_scope="order_query")
        await ts.add_member(t_fault.id, fault_id)
        await ts.add_member(t_order.id, order_id)

        # two handoffs with different intents
        user = User(
            username="end_user",
            email="eu@ex.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER.value,
        )
        db.add(user)
        await db.flush()
        c1 = Conversation(user_id=user.id, title="c1", status=ConversationStatus.TRANSFERRED.value)
        c2 = Conversation(user_id=user.id, title="c2", status=ConversationStatus.TRANSFERRED.value)
        db.add_all([c1, c2])
        await db.flush()
        hs = HandoffService(db)
        h1 = await hs.enqueue(
            conversation_id=c1.id,
            user_id=user.id,
            summary="product fault",
            intent="fault_report",
        )
        h2 = await hs.enqueue(
            conversation_id=c2.id,
            user_id=user.id,
            summary="order issue needs human",
            intent="order_query",
        )
        await db.commit()
        assert h1.intent == "fault_report"
        assert h2.intent == "order_query"

    # fault agent only sees fault_report handoff
    q_fault = await client.get("/api/v1/admin/handoffs", headers=h_fault)
    assert q_fault.status_code == 200, q_fault.text
    ids_fault = {r["id"] for r in q_fault.json()}
    intents_fault = {r.get("intent") for r in q_fault.json()}
    assert h1.id in ids_fault
    assert h2.id not in ids_fault
    assert "order_query" not in intents_fault

    # order agent only sees order_query
    q_order = await client.get("/api/v1/admin/handoffs", headers=h_order)
    assert q_order.status_code == 200
    ids_order = {r["id"] for r in q_order.json()}
    assert h2.id in ids_order
    assert h1.id not in ids_order

    # admin sees both
    q_admin = await client.get("/api/v1/admin/handoffs", headers=admin_h)
    assert q_admin.status_code == 200
    ids_admin = {r["id"] for r in q_admin.json()}
    assert h1.id in ids_admin and h2.id in ids_admin


@pytest.mark.asyncio
async def test_agent_without_team_sees_empty_queue(client: AsyncClient):
    await _register_login(client, "empty_admin")
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "lonely_agent", "email": "la@ex.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": "lonely_agent", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = await client.get("/api/v1/admin/auth/me", headers=headers)
    uid = me.json()["id"]

    factory = async_sessionmaker(dbmod.engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        u = await db.get(User, uid)
        u.role = UserRole.AGENT.value
        user = User(
            username="eu2",
            email="eu2@ex.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER.value,
        )
        db.add(user)
        await db.flush()
        conv = Conversation(user_id=user.id, title="c", status=ConversationStatus.TRANSFERRED.value)
        db.add(conv)
        await db.flush()
        await HandoffService(db).enqueue(
            conversation_id=conv.id,
            user_id=user.id,
            summary="help",
            intent="handoff",
        )
        await db.commit()

    q = await client.get("/api/v1/admin/handoffs", headers=headers)
    assert q.status_code == 200
    assert q.json() == []
