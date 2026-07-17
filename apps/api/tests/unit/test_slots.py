"""Order slot state machine."""

from app.services.agent.slots.state import SlotTracker


def test_extract_order_id():
    t = SlotTracker()
    assert t.extract_order_id("我的订单号是 ORD202401010001") == "ORD202401010001"
    assert t.extract_order_id("单号 1234567890") == "1234567890"


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
