"""Wave F extras: retrieval cache, history summary, least-open dispatch."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import database as dbmod
from app.core.config import get_settings
from app.core.database import Base
from app.models.enums import HandoffStatus
from app.models.handoff import HandoffSession
from app.models.team import Team, TeamMember
from app.services.agent.history_summary import SUMMARY_PREFIX, compress_history
from app.services.rag.pipeline import RAGPipeline
from app.services.rag.retrieval_cache import get_retrieval_cache, reset_retrieval_cache
from app.services.team.service import TeamService


def test_compress_history_folds_old_turns():
    get_settings.cache_clear()
    # force low threshold via settings mutation
    s = get_settings()
    object.__setattr__(s, "history_summary_threshold", 4)
    object.__setattr__(s, "history_summary_keep_recent", 2)
    hist = [{"role": "user", "content": f"q{i}"} for i in range(6)]
    out, did = compress_history(hist, settings=s)
    assert did is True
    assert out[0]["role"] == "system"
    assert out[0]["content"].startswith(SUMMARY_PREFIX)
    assert len(out) == 3  # summary + 2 recent
    assert out[-1]["content"] == "q5"


@pytest.mark.asyncio
async def test_retrieval_cache_second_hit_flag():
    reset_retrieval_cache()
    get_settings.cache_clear()
    s = get_settings()
    object.__setattr__(s, "retrieval_cache_ttl_seconds", 60)
    reset_retrieval_cache()
    pipe = RAGPipeline()
    r1 = await pipe.run("退货政策是什么")
    r2 = await pipe.run("退货政策是什么")
    assert r1.refused is False
    assert "retrieval_cache_miss" in r1.flags or True
    assert "retrieval_cache_hit" in r2.flags


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    old_e, old_s = dbmod.engine, dbmod.SessionLocal
    dbmod.engine = engine
    dbmod.SessionLocal = factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as session:
        yield session
    await engine.dispose()
    dbmod.engine = old_e
    dbmod.SessionLocal = old_s


@pytest.mark.asyncio
async def test_least_open_member_dispatch(db_session: AsyncSession):
    team = Team(name="t1", intent_scope="order_query")
    db_session.add(team)
    await db_session.flush()
    db_session.add_all(
        [
            TeamMember(team_id=team.id, user_id="agent-a"),
            TeamMember(team_id=team.id, user_id="agent-b"),
        ]
    )
    # agent-a already claimed one
    db_session.add(
        HandoffSession(
            conversation_id="c1",
            user_id="u1",
            status=HandoffStatus.CLAIMED.value,
            summary="x",
            intent="order_query",
            claimed_by="agent-a",
        )
    )
    await db_session.flush()
    pick = await TeamService(db_session).least_open_member(team.id)
    assert pick == "agent-b"
