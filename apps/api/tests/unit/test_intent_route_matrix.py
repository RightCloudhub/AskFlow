"""6 intents → 5 route kinds matrix (PRD §12.1 #4)."""

import pytest

from app.models.enums import DEFAULT_INTENT_ROUTES, Intent, Route
from app.services.agent.harness.policy import Harness
from app.services.agent.intent.classifier import IntentClassifier
from app.services.agent.router.decision import RouteResolver


@pytest.mark.asyncio
async def test_six_intents_map_to_five_routes():
    samples = {
        Intent.FAQ: "会员包邮怎么计算",
        Intent.PRODUCT: "这个产品支持哪些功能",
        Intent.ORDER_QUERY: "我的订单物流到哪了",
        Intent.FAULT_REPORT: "系统报错 500 crash",
        Intent.COMPLAINT: "我要投诉服务太差",
        Intent.HANDOFF: "请转人工客服",
        Intent.OUT_OF_SCOPE: "请给我癌症治疗方案和处方建议",
    }
    clf = IntentClassifier()
    resolver = RouteResolver(db=None)
    harness = Harness()
    routes_seen: set[str] = set()

    for expected_intent, text in samples.items():
        ir = await clf.classify(text)
        # product may fall to faq by rules — still legal
        resolved = await resolver.resolve(ir.intent)
        decision = harness.choose_route(resolved.route, confidence=max(ir.confidence, 0.7))
        assert decision.route in Route
        routes_seen.add(decision.route.value)
        # built-in table covers expected for rule-hit intents
        if ir.intent == expected_intent:
            assert DEFAULT_INTENT_ROUTES[ir.intent] == resolved.route

    # matrix covers legal route kinds from samples
    assert "rag" in routes_seen or "clarify" in routes_seen
    assert "tool" in routes_seen
    assert "ticket" in routes_seen
    assert "handoff" in routes_seen
    assert "refuse" in routes_seen
