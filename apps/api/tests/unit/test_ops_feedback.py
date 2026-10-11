"""Ops-feedback fixes P1/P2/P6/P7 (docs/product/ops-feedback-2026-10.md)."""

from __future__ import annotations

from pathlib import Path

from app.services.agent.pipeline.handlers.ticket import _ticket_title
from app.services.chat.side_effects.gap import refusal_reason
from app.services.rag.generator.extractive import extractive_answer, is_near_duplicate
from app.services.rag.query_rewrite.rewriter import QueryRewriter

SYNONYMS = Path(__file__).resolve().parents[4] / "data" / "samples" / "query_synonyms.yaml"


# P1 — the gap reason is why grounding refused, not the always-"skipped" verification result
def test_gap_reason_uses_refusal_reason():
    assert refusal_reason({"result": "skipped", "refusal_reason": "weak_evidence"}) == "weak_evidence"
    assert refusal_reason({"result": "skipped", "refusal_reason": "zero_hit"}) == "zero_hit"


def test_gap_reason_falls_back_when_unknown():
    assert refusal_reason({"result": "skipped"}) == "refused"
    assert refusal_reason(None) == "refused"


# P2 — 账号/帐号 expand to the KB's word 账户
def test_account_synonyms_expand_to_canonical():
    result = QueryRewriter(SYNONYMS).rewrite("账号被锁了怎么办")
    assert "账户" in result.rewritten


# P6 — ticket titles are customer-visible: Chinese prefix, still stable for merging
def test_ticket_title_has_chinese_prefix():
    assert _ticket_title("complaint", "商品质量太差了") == "【投诉】商品质量太差了"
    assert _ticket_title("fault_report", "耳机没声音") == "【故障】耳机没声音"
    assert _ticket_title("unknown_intent", "") == "【工单】用户请求"
    assert _ticket_title("complaint", "同一句话") == _ticket_title("complaint", "同一句话")


# P7 — the same fact from two documents is said once
def test_near_duplicate_detection():
    assert is_near_duplicate("退款在仓库验收通过后 3-5 个工作日原路返回；", "退款将在审核通过后3-5个工作日原路返回。")
    assert not is_near_duplicate("退款在仓库验收通过后 3-5 个工作日原路返回；", "使用优惠券的订单按实付金额退款。")


def test_extractive_answer_drops_cross_source_duplicate():
    sources = [
        {"index": 1, "text": "退款在仓库验收通过后 3-5 个工作日原路返回；使用优惠券的订单按实付金额退款。"},
        {"index": 2, "text": "退款将在审核通过后3-5个工作日原路返回。"},
    ]
    answer = extractive_answer("退款多久能到账", sources)
    assert answer.count("3-5") == 1
    assert "[1]" in answer
