"""P3 (M4): notify is a first-class operation; channel choice follows preference and health."""

import pytest

from app.services.agent.domains.notify import (
    NOTIFY_CHAT,
    NOTIFY_EMAIL,
    NOTIFY_GOAL,
    NOTIFY_PERMISSION,
    notify_agent,
    notify_candidates,
    notify_operations,
)
from app.services.agent.service.contracts import Environment, OperationCall
from app.services.agent.service.driver import advance
from app.services.agent.service.executor import Executor
from app.services.agent.service.registry import OperationRegistry
from tests.unit.test_service_agent import SCOPE, store, task

__all__ = ["store"]

CONVERSATION = "conv-1"
MESSAGE = "您的订单已发货"
CAPABLE_CHANNELS = {
    "email": {"capable": True, "health": "ok"},
    "chat": {"capable": True, "health": "ok"},
}


class Recorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, request):
        self.calls.append(request.arguments["channel"])
        return {"status": "ok", "message_id": f"msg-{len(self.calls)}"}


def notify_env(*, preference=None, channels=None):
    preferences = {"contact_channel": preference} if preference else {}
    return Environment(
        scope=SCOPE,
        permissions=frozenset({NOTIFY_PERMISSION}),
        available_operations=frozenset({NOTIFY_EMAIL, NOTIFY_CHAT}),
        facts={"channels": channels if channels is not None else CAPABLE_CHANNELS},
        preferences=preferences,
    )


def notify_task():
    original = task()
    original.goal = NOTIFY_GOAL
    original.completion_condition = NOTIFY_GOAL
    original.inputs = {"conversation_id": CONVERSATION, "message": MESSAGE}
    return original


def notify_call(operation_id, *, key):
    return OperationCall(
        operation_id=operation_id,
        key=key,
        arguments={
            "conversation_id": CONVERSATION,
            "channel": operation_id.rsplit(".", 1)[-1],
            "message": MESSAGE,
        },
    )


def test_notify_contract_is_separate_from_business_effects():
    ops = {op.operation_id: op for op in notify_operations(sender=Recorder())}
    assert set(ops) == {NOTIFY_EMAIL, NOTIFY_CHAT}
    for op in ops.values():
        assert op.effect == "notify"
        assert op.permission == NOTIFY_PERMISSION


def test_preferred_channel_gets_better_priority():
    candidates = notify_candidates(notify_task(), notify_env(preference="email"))
    by_op = {c.call.operation_id: c for c in candidates}
    assert set(by_op) == {NOTIFY_EMAIL, NOTIFY_CHAT}
    assert by_op[NOTIFY_EMAIL].priority < by_op[NOTIFY_CHAT].priority


@pytest.mark.asyncio
async def test_degraded_channel_is_rejected_with_reason(store):
    recorder = Recorder()
    channels = {
        "email": {"capable": True, "health": "degraded"},
        "chat": {"capable": True, "health": "ok"},
    }

    async def observe(_task):
        return notify_env(preference="email", channels=channels)

    agent = notify_agent(store, observe, sender=recorder)
    original = notify_task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.status == "resolved"
    assert result.decisions[0].selected == NOTIFY_CHAT
    assert result.decisions[0].rejected[NOTIFY_EMAIL] == "precondition_failed"
    assert recorder.calls == ["chat"]


@pytest.mark.asyncio
async def test_missing_channel_capability_is_rejected(store):
    recorder = Recorder()
    channels = {"chat": {"capable": True, "health": "ok"}}

    async def observe(_task):
        return notify_env(channels=channels)

    agent = notify_agent(store, observe, sender=recorder)
    original = notify_task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.decisions[0].rejected[NOTIFY_EMAIL] == "precondition_failed"
    assert recorder.calls == ["chat"]


@pytest.mark.asyncio
async def test_duplicate_notify_call_sends_once(store):
    recorder = Recorder()
    executor = Executor(OperationRegistry(notify_operations(sender=recorder)), store)
    original = notify_task()
    await store.create(original)
    env = notify_env()
    request = notify_call(NOTIFY_CHAT, key="notify-1")
    first = await executor.execute(original, request, env=env)
    restored = await store.load(original.task_id, SCOPE)
    again = await executor.execute(restored, request, env=env)
    assert first.status == "succeeded"
    assert again == first
    assert recorder.calls == ["chat"]


@pytest.mark.asyncio
async def test_notify_failure_does_not_touch_business_evidence(store):
    async def broken(_request):
        raise RuntimeError("smtp down")

    executor = Executor(OperationRegistry(notify_operations(sender=broken)), store)
    original = notify_task()
    await store.create(original)
    receipt = await executor.execute(
        original, notify_call(NOTIFY_EMAIL, key="notify-2"), env=notify_env()
    )
    assert receipt.status == "unknown"
    restored = await store.load(original.task_id, SCOPE)
    assert restored.evidence == []
