"""Deterministic fact extraction from explicit user statements (arch §9.8)."""

from app.services.agent.memory.extract import extract_facts


def test_language_preference_detected():
    proposals = extract_facts("以后用英文回复我")
    assert [(p.key, p.value) for p in proposals] == [("preferred_language", "en-US")]


def test_english_language_phrase_detected():
    proposals = extract_facts("Please reply in English from now on")
    assert proposals[0].key == "preferred_language" and proposals[0].value == "en-US"


def test_contact_preference_detected():
    proposals = extract_facts("以后用邮件联系我")
    assert [(p.key, p.value) for p in proposals] == [("contact_channel", "email")]


def test_order_id_detected():
    proposals = extract_facts("我的订单号是 ORD202401010001")
    assert [(p.key, p.value) for p in proposals] == [("last_order_id", "ORD202401010001")]


def test_plain_message_extracts_nothing():
    assert extract_facts("你好，退货政策是什么？") == []


def test_proposals_are_bounded():
    text = "以后用英文回复我，以后用邮件联系我，我的订单号是 ORD202401010001"
    proposals = extract_facts(text)
    assert len(proposals) <= 3
    assert {p.key for p in proposals} == {"preferred_language", "contact_channel", "last_order_id"}
