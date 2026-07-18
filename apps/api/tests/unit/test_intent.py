"""Intent rule classifier (PRD §4.3.1)."""

import pytest

from app.models.enums import Intent
from app.services.agent.intent.classifier import IntentClassifier


@pytest.mark.asyncio
async def test_order_query():
    r = await IntentClassifier().classify("我的订单物流到哪了")
    assert r.intent == Intent.ORDER_QUERY
    assert r.source == "rule"


@pytest.mark.asyncio
async def test_fault_report():
    r = await IntentClassifier().classify("页面报错 500 crash")
    assert r.intent == Intent.FAULT_REPORT


@pytest.mark.asyncio
async def test_bare_number_not_fault():
    r = await IntentClassifier().classify("房间号是500")
    assert r.intent != Intent.FAULT_REPORT


@pytest.mark.asyncio
async def test_complaint():
    r = await IntentClassifier().classify("我要投诉，非常不满")
    assert r.intent == Intent.COMPLAINT


@pytest.mark.asyncio
async def test_handoff_requires_cooccurrence():
    r = await IntentClassifier().classify("转人工客服")
    assert r.intent == Intent.HANDOFF


@pytest.mark.asyncio
async def test_bare_agent_does_not_handoff():
    r = await IntentClassifier().classify("is there an agent model config?")
    assert r.intent != Intent.HANDOFF


@pytest.mark.asyncio
async def test_default_faq():
    r = await IntentClassifier().classify("会员包邮怎么算")
    assert r.intent == Intent.FAQ
