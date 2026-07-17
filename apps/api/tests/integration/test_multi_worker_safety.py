"""Concurrent handoff claim/sweep safety (enterprise multi-worker)."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import database as dbmod
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus, HandoffStatus, UserRole
from app.models.handoff import HandoffSession
from app.models.user import User
from app.core.security import hash_password
from app.services.handoff.service import HandoffService
from app.services.handoff.timeout import HandoffTimeoutSweeper
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_concurrent_claim_only_one_wins(client: AsyncClient):
    # ensure tables via client bootstrap
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "mw1", "email": "mw1@e.com", "password": "password123"},
    )
    factory = async_sessionmaker(dbmod.engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        u = User(
            username="mw_user",
            email="mwu@e.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER.value,
        )
        db.add(u)
        await db.flush()
        conv = Conversation(user_id=u.id, title="c", status=ConversationStatus.TRANSFERRED.value)
        db.add(conv)
        await db.flush()
        hs = HandoffSession(
            conversation_id=conv.id,
            user_id=u.id,
            status=HandoffStatus.QUEUED.value,
            summary="need help",
        )
        db.add(hs)
        await db.commit()
        hid = hs.id

    async def claim_as(agent_id: str):
        async with factory() as session:
            try:
                row = await HandoffService(session).claim(hid, agent_id)
                await session.commit()
                return ("ok", row.claimed_by)
            except HTTPException as exc:
                await session.rollback()
                return ("err", exc.status_code)

    r1, r2, r3 = await asyncio.gather(
        claim_as("agent-a"),
        claim_as("agent-b"),
        claim_as("agent-c"),
    )
    oks = [r for r in (r1, r2, r3) if r[0] == "ok"]
    errs = [r for r in (r1, r2, r3) if r[0] == "err"]
    assert len(oks) == 1
    assert all(e[1] == 409 for e in errs)


@pytest.mark.asyncio
async def test_concurrent_sweep_single_ticket(client: AsyncClient):
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": "mw2", "email": "mw2@e.com", "password": "password123"},
    )
    factory = async_sessionmaker(dbmod.engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        u = User(
            username="mw_user2",
            email="mwu2@e.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER.value,
        )
        db.add(u)
        await db.flush()
        conv = Conversation(user_id=u.id, title="c2", status=ConversationStatus.TRANSFERRED.value)
        db.add(conv)
        await db.flush()
        hs = HandoffSession(
            conversation_id=conv.id,
            user_id=u.id,
            status=HandoffStatus.QUEUED.value,
            summary="timeout me",
        )
        db.add(hs)
        await db.flush()
        hs.created_at = datetime.now(UTC) - timedelta(hours=2)
        await db.commit()
        hid = hs.id

    async def sweep_once():
        async with factory() as session:
            outcomes = await HandoffTimeoutSweeper(session).sweep()
            await session.commit()
            return outcomes

    o1, o2 = await asyncio.gather(sweep_once(), sweep_once())
    all_out = o1 + o2
    # only one successful timeout for this handoff
    matched = [o for o in all_out if o["handoff_id"] == hid]
    assert len(matched) == 1
    assert matched[0]["ticket_id"]
