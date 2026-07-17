"""Agent run persistence + get-by-run_id (S-08) via real store and side-effect."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.plugins.types import ChatTurnContext
from app.services.agent.cost.ledger import CostLedger
from app.services.agent.cost.store import CostStore
from app.services.agent.run_store import AgentRunStore, build_run_steps
from app.services.chat.side_effects.agent_run import AgentRunSideEffect
from app.services.chat.side_effects.cost import CostSideEffect
from app.utils.ids import new_run_id

PROMPT_TOKENS = 100
COMPLETION_TOKENS = 50
RECENT_LIMIT = 10


async def _session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


def _sample_cost(run_id: str) -> dict:
    ledger = CostLedger(run_id)
    ledger.record(
        purpose="rag_generate",
        model="gpt-4o-mini",
        prompt_tokens=PROMPT_TOKENS,
        completion_tokens=COMPLETION_TOKENS,
    )
    return ledger, ledger.summary()


@pytest.mark.asyncio
async def test_agent_run_save_and_get_with_cost():
    engine, factory = await _session_factory()
    run_id = new_run_id()
    async with factory() as db:
        user = User(
            username="run_u",
            email="run@e.com",
            hashed_password=hash_password("password123"),
            role=UserRole.ADMIN.value,
        )
        db.add(user)
        await db.flush()
        ledger, cost = _sample_cost(run_id)
        await CostStore(db).persist_ledger(ledger)
        turn = ChatTurnContext(
            db=db,
            conversation_id="conv-1",
            user_id=user.id,
            content="how to reset password?",
            intent="faq",
            route="rag",
            refused=False,
            verification={"ok": True},
            run_id=run_id,
            cost=cost,
            flags=["grounded"],
        )
        se = await CostSideEffect().apply({}, turn)
        se = await AgentRunSideEffect().apply(se, turn)
        assert se.get("agent_run_saved") is True
        store = AgentRunStore(db)
        row = await store.get_by_run_id(run_id)
        assert row is not None
        assert row.route == "rag" and len(row.steps) >= 2
        cost_view = await store.cost_for_run(run_id)
        assert cost_view["entry_count"] >= 1
        assert cost_view["entries"][0]["purpose"] == "rag_generate"
        recent = await store.list_recent(limit=RECENT_LIMIT)
        assert any(r.run_id == run_id for r in recent)
    await engine.dispose()


def test_build_run_steps_includes_flags_and_models():
    steps = build_run_steps(
        route="refuse",
        intent="out_of_scope",
        flags=["oos", "weak_evidence"],
        cost={
            "entries": [
                {
                    "purpose": "intent_classify",
                    "model": "gpt-4o-mini",
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "estimated_usd": 0.0,
                }
            ]
        },
        refused=True,
    )
    kinds = [s["kind"] for s in steps]
    assert kinds[0] == "route"
    assert "flag" in kinds and "model" in kinds
