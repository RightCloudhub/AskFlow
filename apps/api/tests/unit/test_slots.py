"""Order slot state machine + pipeline abandon/clear regressions."""

import pytest

from app.services.agent.pipeline.runner import MessagePipeline
from app.services.agent.slots.state import SlotTracker
from app.utils.merge import merge_patch


def test_extract_order_id():
    t = SlotTracker()
    assert t.extract_order_id("我的订单号是 ORD202401010001") == "ORD202401010001"
    assert t.extract_order_id("单号 1234567890") == "1234567890"
    assert t.extract_order_id("ORD202401010001查一下") == "ORD202401010001"


def test_extract_rejects_phone_and_date():
    t = SlotTracker()
    assert t.extract_order_id("我的手机号是13800138000") is None
    assert t.extract_order_id("今天是20240115") is None
    assert t.extract_order_id("电话13912345678想投诉") is None


def test_ask_then_fill():
    t = SlotTracker()
    meta = t.start_order_slot({})
    d1 = t.decide("还没有", meta)
    assert d1.action == "ask"
    meta2 = t.apply_patch(meta, d1.patch)
    d2 = t.decide("订单号 ORD999888777", meta2)
    assert d2.action == "filled"
    assert d2.order_id == "ORD999888777"


def test_abandon_on_max_turns():
    t = SlotTracker(max_turns=1)
    meta = t.start_order_slot({})
    d1 = t.decide("不知道", meta)
    meta = t.apply_patch(meta, d1.patch)
    d2 = t.decide("还是不知道", meta)
    assert d2.action == "abandon"
    assert d2.message
    assert d2.patch == {"pending_slot": None}


def test_abandon_on_intent_switch():
    t = SlotTracker()
    meta = t.start_order_slot({})
    d = t.decide(
        "我要投诉你们服务太差",
        meta,
        new_intent="complaint",
        new_intent_confidence=0.85,
    )
    assert d.action == "abandon"
    assert d.patch == {"pending_slot": None}


@pytest.mark.asyncio
async def test_pipeline_abandon_clears_pending_and_shows_message():
    p = MessagePipeline(None)
    meta: dict = {}
    r1 = await p.handle("查一下我的订单物流", history=[], metadata=meta)
    meta = merge_patch(meta, r1.metadata_patch)
    assert meta.get("pending_slot") is not None

    for _ in range(3):
        r = await p.handle("不知道", history=[], metadata=meta)
        meta = merge_patch(meta, r.metadata_patch)

    # max_slot_turns=3 → next wait abandons
    r_ab = await p.handle("还是没有", history=[], metadata=meta)
    assert "slot_abandon" in r_ab.flags or "未能获取订单号" in r_ab.answer
    assert r_ab.metadata_patch.get("pending_slot") is None
    meta = merge_patch(meta, r_ab.metadata_patch)
    assert "pending_slot" not in meta


@pytest.mark.asyncio
async def test_pipeline_phone_complaint_not_tool_after_stuck_slot():
    p = MessagePipeline(None)
    meta: dict = {}
    r1 = await p.handle("查订单", history=[], metadata=meta)
    meta = merge_patch(meta, r1.metadata_patch)
    for _ in range(4):
        r = await p.handle("没有", history=[], metadata=meta)
        meta = merge_patch(meta, r.metadata_patch)

    r = await p.handle(
        "我的电话是13912345678，想投诉服务太差",
        history=[],
        metadata=meta,
    )
    assert r.route == "ticket"
    assert r.intent == "complaint"
    assert "tool_mock" not in (r.flags or [])
    assert "pending_slot" not in merge_patch(meta, r.metadata_patch)


@pytest.mark.asyncio
async def test_pipeline_intent_switch_clears_slot():
    p = MessagePipeline(None)
    meta: dict = {}
    r1 = await p.handle("查一下订单物流", history=[], metadata=meta)
    meta = merge_patch(meta, r1.metadata_patch)
    assert meta.get("pending_slot")
    r2 = await p.handle("我要投诉，非常不满", history=[], metadata=meta)
    meta = merge_patch(meta, r2.metadata_patch)
    assert "pending_slot" not in meta
    assert r2.route == "ticket"
    assert r2.intent == "complaint"
