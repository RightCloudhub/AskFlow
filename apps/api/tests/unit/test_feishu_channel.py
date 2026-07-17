"""Feishu event parse + pipeline handle (no live Feishu API)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.services.channels.feishu.service import FeishuService


def _settings(**kwargs) -> Settings:
    base = dict(
        ASKFLOW_ENV="test",
        SECRET_KEY="test-secret-key-not-for-prod-xx",
        FEISHU_VERIFICATION_TOKEN="vt-test",
    )
    base.update(kwargs)
    return Settings(**base)


def test_url_verification_challenge():
    svc = FeishuService.__new__(FeishuService)
    svc.settings = _settings()
    parsed = FeishuService.parse_event(
        svc, {"type": "url_verification", "challenge": "abc123", "token": "vt-test"}
    )
    assert parsed == "abc123"


def test_parse_v2_text_message():
    svc = FeishuService.__new__(FeishuService)
    svc.settings = _settings()
    body = {
        "header": {"event_type": "im.message.receive_v1", "token": "vt-test"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou_user_1"}},
            "message": {
                "message_id": "om_1",
                "chat_id": "oc_1",
                "message_type": "text",
                "content": json.dumps({"text": "退货怎么申请"}),
            },
        },
    }
    inbound = FeishuService.parse_event(svc, body)
    assert inbound is not None and not isinstance(inbound, str)
    assert inbound.open_id == "ou_user_1"
    assert "退货" in inbound.text


@pytest.mark.asyncio
async def test_handle_message_runs_pipeline():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        svc = FeishuService(db, settings=_settings())
        body = {
            "header": {"event_type": "im.message.receive_v1", "token": "vt-test"},
            "token": "vt-test",
            "event": {
                "sender": {"sender_id": {"open_id": "ou_pipeline"}},
                "message": {
                    "message_id": "om_x",
                    "chat_id": "oc_x",
                    "message_type": "text",
                    "content": json.dumps({"text": "你好，退货政策是什么？"}),
                },
            },
        }
        result = await svc.handle_payload(body)
        assert result.kind == "message"
        assert result.run_id
        assert result.reply_text
        assert result.reply_status == "local_only"

        bad = await svc.handle_payload({**body, "token": "wrong"})
        assert bad.kind == "ignored"
        assert bad.reply_status == "bad_token"
    await engine.dispose()
