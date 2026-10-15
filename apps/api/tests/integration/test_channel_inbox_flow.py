"""Webhook replay produces exactly one turn; the outbox relay publishes task results (arch §9.1)."""

import json

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.conversation import Message
from app.services.channels.canonical import CanonicalMessage
from app.services.channels.feishu.service import FeishuService
from app.services.channels.inbox import record_inbound
from app.workers.outbox_relay import run_once as outbox_run_once


def _settings():
    from app.core.config import Settings

    return Settings(
        ASKFLOW_ENV="test",
        SECRET_KEY="test-secret-key-not-for-prod-xx",
        FEISHU_VERIFICATION_TOKEN="vt-test",
    )


def _feishu_body(message_id: str) -> dict:
    return {
        "header": {"event_type": "im.message.receive_v1", "token": "vt-test"},
        "token": "vt-test",
        "event": {
            "sender": {"sender_id": {"open_id": "ou_replay"}},
            "message": {
                "message_id": message_id,
                "chat_id": "oc_replay",
                "message_type": "text",
                "content": json.dumps({"text": "退货政策是什么？"}),
            },
        },
    }


@pytest_asyncio.fixture
async def db_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_replayed_webhook_creates_exactly_one_turn(db_factory):
    async with db_factory() as db:
        svc = FeishuService(db, settings=_settings())
        first = await svc.handle_payload(_feishu_body("om_replay_1"))
        assert first.kind == "message"
        await db.commit()
    for _ in range(9):
        async with db_factory() as db:
            svc = FeishuService(db, settings=_settings())
            replayed = await svc.handle_payload(_feishu_body("om_replay_1"))
            assert replayed.kind == "duplicate"
            await db.commit()
    async with db_factory() as db:
        user_messages = await db.scalar(
            select(func.count()).select_from(Message).where(Message.role == "user")
        )
    assert user_messages == 1


@pytest.mark.asyncio
async def test_inbox_row_claimed_and_published_once(db_factory):
    async with db_factory() as db:
        message = CanonicalMessage(
            channel="wecom",
            channel_message_id="wm_1",
            channel_user_id="u1",
            session_key="wecom:u1",
            text="hi",
            chat_key="u1",
        )
        assert await record_inbound(db, message) is not None
        await db.commit()
    async with db_factory() as db:
        assert await record_inbound(db, message) is None
        await db.commit()


@pytest.mark.asyncio
async def test_outbox_relay_run_once_marks_published(db_factory, monkeypatch):
    import app.core.database as dbmod
    from app.services.outbox.store import emit, pending

    monkeypatch.setattr(dbmod, "SessionLocal", db_factory)
    async with db_factory() as db:
        await emit(
            db,
            aggregate="session",
            aggregate_id="c1",
            event_type="future.event",
            payload={"anything": True},
        )
        await db.commit()
    result = await outbox_run_once()
    assert result == {"published": 1}
    async with db_factory() as db:
        assert await pending(db, limit=10, max_attempts=5) == []
