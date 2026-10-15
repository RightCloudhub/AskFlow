"""Wave C: outbox store, inbox claims, renderer/splitting, delivery retries, WS registry."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.conversation import Conversation
from app.models.enums import UserRole
from app.models.notify import NotificationLog
from app.models.outbox import OutboxEvent
from app.models.user import User
from app.services.channels.canonical import CanonicalMessage
from app.services.channels.inbox import (
    claim_batch,
    mark_published,
    record_failure,
    record_inbound,
)
from app.services.chat.ws_registry import WsRegistry
from app.services.outbound.delivery import (
    STATUS_LOCAL_ONLY,
    STATUS_RATE_LIMITED,
    STATUS_SENT,
    OutboundDelivery,
)
from app.services.outbound.render import render_parts
from app.services.outbound.settings import OutboundSettings
from app.services.outbox.relay import publish_event
from app.services.outbox.store import emit, pending
from app.services.outbox.store import mark_published as outbox_mark
from app.services.outbox.store import record_failure as outbox_fail

FAST_RETRY = OutboundSettings(OUTBOUND_RETRY_BASE_SECONDS=0.1)


@pytest_asyncio.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'wavec.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def message(message_id: str, *, text: str = "你好", chat_key: str = "oc_1") -> CanonicalMessage:
    return CanonicalMessage(
        channel="feishu",
        channel_message_id=message_id,
        channel_user_id="ou_1",
        session_key=f"feishu:{chat_key}",
        text=text,
        chat_key=chat_key,
    )


@pytest.mark.asyncio
async def test_outbox_emit_publish_and_failure_attempts(sessions):
    async with sessions.begin() as db:
        await emit(db, aggregate="session", aggregate_id="c1", event_type="task.result", payload={"x": 1})
    async with sessions.begin() as db:
        rows = await pending(db, limit=10, max_attempts=3)
        assert len(rows) == 1
        await outbox_fail(db, rows[0], "boom")
    async with sessions.begin() as db:
        rows = await pending(db, limit=10, max_attempts=3)
        assert rows[0].attempts == 1 and rows[0].last_error == "boom"
        await outbox_mark(db, rows[0])
    async with sessions.begin() as db:
        assert await pending(db, limit=10, max_attempts=3) == []


@pytest.mark.asyncio
async def test_inbox_dedup_and_session_ordering(sessions):
    async with sessions.begin() as db:
        first = await record_inbound(db, message("m1"))
        assert first is not None
        assert await record_inbound(db, message("m1")) is None  # replay
        second = await record_inbound(db, message("m2"))
        assert second is not None
    async with sessions() as db:
        claimed = await claim_batch(db, limit=10, max_attempts=3)
        assert [row.channel_message_id for row in claimed] == ["m1"]  # in-order per session
        await mark_published(db, claimed[0])
        await db.commit()
    async with sessions() as db:
        claimed = await claim_batch(db, limit=10, max_attempts=3)
        assert [row.channel_message_id for row in claimed] == ["m2"]


@pytest.mark.asyncio
async def test_inbox_lease_expiry_allows_reclaim(sessions):
    async with sessions.begin() as db:
        await record_inbound(db, message("m3"))
    async with sessions() as db:
        claimed = await claim_batch(db, limit=10, max_attempts=3)
        assert len(claimed) == 1
        assert await claim_batch(db, limit=10, max_attempts=3) == []  # leased
        row = await db.get(type(claimed[0]), claimed[0].id)
        row.lease_until = datetime.now(UTC) - timedelta(seconds=1)
        await db.commit()
    async with sessions() as db:
        reclaimed = await claim_batch(db, limit=10, max_attempts=3)
        assert len(reclaimed) == 1
        await record_failure(db, reclaimed[0], "process_error")
        await db.commit()


def test_render_splits_long_text_at_soft_breaks():
    text = "\n".join(f"line {i} " + "x" * 60 for i in range(60))
    parts = render_parts(text, channel="wecom")
    assert len(parts) > 1
    assert all(len(part) <= 2048 for part in parts)
    assert "".join(parts).replace("\n", "") == text.replace("\n", "")


@pytest.mark.asyncio
async def test_delivery_retries_then_succeeds(sessions):
    attempts = []

    async def flaky(*, target, text):
        attempts.append(target)
        return "http_500" if len(attempts) < 2 else STATUS_SENT

    async with sessions.begin() as db:
        delivery = OutboundDelivery(FAST_RETRY, sender_resolver=lambda channel: flaky)
        status = await delivery.deliver(db, channel="feishu", target="oc_1", text="hello")
    assert status == STATUS_SENT and len(attempts) == 2


@pytest.mark.asyncio
async def test_delivery_failure_is_logged_and_local_only_skips(sessions):
    async def broken(*, target, text):
        raise RuntimeError("connection refused")

    async with sessions.begin() as db:
        delivery = OutboundDelivery(FAST_RETRY, sender_resolver=lambda channel: broken)
        status = await delivery.deliver(db, channel="feishu", target="oc_1", text="hello")
        assert status.startswith("error:")
        delivery_none = OutboundDelivery(FAST_RETRY, sender_resolver=lambda channel: None)
        assert (
            await delivery_none.deliver(db, channel="wecom", target="u1", text="hi")
            == STATUS_LOCAL_ONLY
        )
    async with sessions() as db:
        rows = list(await db.scalars(select(NotificationLog).order_by(NotificationLog.created_at)))
    assert next(row.status for row in rows).startswith("error:")
    assert rows[1].status == STATUS_LOCAL_ONLY


@pytest.mark.asyncio
async def test_delivery_rate_limit_blocks_second_send(sessions):
    from app.services.outbound import delivery as delivery_mod

    delivery_mod._BUCKETS.pop("dingtalk", None)  # buckets are process-global

    async def ok(*, target, text):
        return STATUS_SENT

    async with sessions.begin() as db:
        delivery = OutboundDelivery(
            OutboundSettings(OUTBOUND_RATE_PER_MINUTE=1, OUTBOUND_RETRY_BASE_SECONDS=0.1),
            sender_resolver=lambda channel: ok,
        )
        first = await delivery.deliver(db, channel="dingtalk", target="u1", text="a")
        second = await delivery.deliver(db, channel="dingtalk", target="u1", text="b")
    assert first == STATUS_SENT and second == STATUS_RATE_LIMITED


@pytest.mark.asyncio
async def test_ws_registry_broadcast_and_cleanup():
    class FakeSocket:
        def __init__(self, fail=False):
            self.sent = []
            self.fail = fail

        async def send_json(self, payload):
            if self.fail:
                raise RuntimeError("closed")
            self.sent.append(payload)

    registry = WsRegistry()
    good, bad = FakeSocket(), FakeSocket(fail=True)
    registry.register("c1", good)
    registry.register("c1", bad)
    sent = await registry.broadcast("c1", {"type": "proactive"})
    assert sent == 1 and good.sent[0]["type"] == "proactive"
    assert registry.count("c1") == 1  # failing socket removed


@pytest.mark.asyncio
async def test_relay_pushes_task_result_to_channel(sessions):
    pushed = []

    class FakeDelivery:
        async def deliver(self, db, *, channel, target, text, event_type):
            pushed.append((channel, target, text, event_type))
            return STATUS_SENT

    async with sessions.begin() as db:
        user = User(username="u", email="u@example.com", hashed_password="x", role=UserRole.USER.value)
        db.add(user)
        await db.flush()
        conv = Conversation(
            user_id=user.id,
            title="t",
            status="active",
            metadata_json={"channel": "feishu", "channel_chat_key": "oc_9"},
        )
        db.add(conv)
        await db.flush()
        event = await emit(
            db,
            aggregate="session",
            aggregate_id=conv.id,
            event_type="task.result",
            payload={"conversation_id": conv.id, "content": "订单已完成", "task_id": "t1"},
        )
        await publish_event(db, event, delivery=FakeDelivery())
    assert pushed == [("feishu", "oc_9", "订单已完成", "task.result")]


@pytest.mark.asyncio
async def test_relay_acks_unknown_event_types(sessions):
    async with sessions.begin() as db:
        event = await emit(db, aggregate="x", aggregate_id="1", event_type="future.event", payload={})
        await publish_event(db, event)
    async with sessions() as db:
        rows = list(await db.scalars(select(OutboxEvent)))
    assert len(rows) == 1  # publish is a no-op; the relay marks it published
