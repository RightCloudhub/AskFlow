"""Offline-ish probes for AskFlow context engineering acceptance criteria.

Run from repo root with:  apps/api/.venv/bin/python evals/probes/context_probe.py
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("ASKFLOW_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from app.core.config import get_settings  # noqa: E402
from app.services.agent.harness.policy import Harness  # noqa: E402
from app.services.agent.history_summary import compress_history  # noqa: E402
from app.services.rag.context.assembler import ContextAssembler  # noqa: E402
from app.services.rag.grounding.evaluator import GroundingEvaluator  # noqa: E402
from app.services.rag.query_rewrite.rewriter import QueryRewriter  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} :: {detail}")


def test_history_turn_window() -> None:
    s = get_settings()
    h = Harness()
    hist = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg-{i}"} for i in range(30)]
    r = h.prepare("继续", hist)
    check(
        "L2 历史条数上限 max_history_messages",
        len(r.history) <= s.max_history_messages and "history_truncated" in r.flags,
        f"used={len(r.history)} limit={s.max_history_messages} flags={r.flags}",
    )


def test_history_char_budget() -> None:
    s = get_settings()
    h = Harness()
    hist = [{"role": "user", "content": "x" * 1900} for _ in range(5)]
    r = h.prepare("继续", hist)
    total = sum(len(m["content"]) for m in r.history)
    check(
        "L2 历史字符预算 max_history_chars",
        total <= s.max_history_chars and "history_char_budget" in r.flags,
        f"chars={total} limit={s.max_history_chars} flags={r.flags}",
    )


def test_history_msg_truncation() -> None:
    h = Harness()
    r = h.prepare("继续", [{"role": "user", "content": "y" * 2500}])
    content = r.history[-1]["content"]
    check(
        "L2 单条消息截断 + flag",
        "history_msg_truncated" in r.flags and len(content) <= 2000,
        f"len={len(content)} flags={r.flags}",
    )
    check(
        "L2 单条截断可配置（文档 CONTEXT_MAX_CHARS_PER_MSG=1200）",
        len(content) == 1200,
        f"实际截断到 {len(content)}，代码硬编码 2000，无配置项",
    )


def test_staff_mirror() -> None:
    h = Harness()
    r = h.prepare("继续", [{"role": "staff", "content": "人工已处理"}])
    check(
        "L2 staff→assistant 镜像",
        r.history and r.history[0]["role"] == "assistant" and "staff_mirrored" in r.flags,
        f"history={r.history} flags={r.flags}",
    )


def test_illegal_role_drop() -> None:
    h = Harness()
    r = h.prepare("继续", [{"role": "tool", "content": "internal"}, {"role": "user", "content": "hi"}])
    check(
        "L2 非法 role 丢弃",
        all(m["content"] != "internal" for m in r.history) and "dropped_illegal_role" in r.flags,
        f"history={r.history} flags={r.flags}",
    )


def test_system_role_leak() -> None:
    h = Harness()
    r = h.prepare("继续", [{"role": "system", "content": "SECRET POLICY"}])
    leaked = any(m["role"] == "system" for m in r.history)
    check(
        "L0/L2 system 消息不得进入 LLM 历史",
        not leaked,
        f"system 被保留={leaked} history={r.history}",
    )


def test_summary_compression() -> None:
    s = get_settings()
    hist = [{"role": "user", "content": f"q{i}"} for i in range(s.history_summary_threshold + 3)]
    out, did = compress_history(hist, settings=s)
    check(
        "E26 中段摘要压缩",
        did and len(out) == s.history_summary_keep_recent + 1,
        f"threshold={s.history_summary_threshold} keep={s.history_summary_keep_recent} out_len={len(out)}",
    )
    # integration through harness flags
    h = Harness()
    r = h.prepare("继续", hist)
    check(
        "E26 harness 暴露 history_summarized flag",
        "history_summarized" in r.flags,
        f"flags={r.flags}",
    )


def test_rewrite_coreference() -> None:
    rw = QueryRewriter()
    hist = [{"role": "assistant", "content": "退货政策是 7 天无理由。"}]
    r = rw.rewrite("它超过 7 天还能退吗", history=hist)
    resolved = "退货" in r.rewritten or r.strategy == "llm"
    check(
        "L4 多轮指代消解（借助 history rewrite）",
        resolved,
        f"strategy={r.strategy} rewritten={r.rewritten!r}（history 被忽略）",
    )
    r2 = rw.rewrite("怎么退换货")
    check(
        "L4 同义词规则改写",
        r2.strategy in {"rule", "none"},
        f"strategy={r2.strategy} rewritten={r2.rewritten!r}",
    )


class _Hit:
    def __init__(self, score: float) -> None:
        self.score = score
        self.doc_id = "d1"
        self.source = "seed.md"
        self.text = "退货运费说明"


def test_grounding_threshold() -> None:
    s = get_settings()
    ev = GroundingEvaluator()
    weak = ev.evaluate([_Hit(0.10)])
    strong = ev.evaluate([_Hit(0.80)])
    check(
        "L3 弱证据拒答（低于阈值）",
        weak.pass_through is False and weak.reason == "weak_evidence",
        f"thr={s.grounding_threshold} score=0.10 pass={weak.pass_through} reason={weak.reason}",
    )
    check(
        "L3 强证据放行",
        strong.pass_through is True,
        f"score=0.80 pass={strong.pass_through}",
    )


def test_context_assembler_trace() -> None:
    bundle = ContextAssembler().assemble(
        question="退货政策",
        history=[{"role": "user", "content": "你好"}],
        sources=[{"index": 1, "source": "a.md", "text": "7天无理由"}],
    )
    required = {
        "run_id",
        "trace_id",
        "policy_version",
        "history",
        "query",
        "retrieval",
        "budget",
        "flags",
        "route",
        "intent",
    }
    check(
        "ContextTrace 完整字段（文档 §7）",
        required.issubset(bundle.trace.keys()),
        f"trace={bundle.trace}；缺失={sorted(required - set(bundle.trace))}",
    )
    check(
        "ContextAssembler 至少产出基础 trace",
        {"history_msgs", "evidence_count", "evidence_chars"}.issubset(bundle.trace.keys()),
        f"trace={bundle.trace}",
    )
    has_roles_only = all(m["role"] in {"system", "user", "assistant"} for m in bundle.messages)
    check(
        "L2/L3 组装消息 role 合法",
        has_roles_only,
        f"roles={[m['role'] for m in bundle.messages]}",
    )


def test_transferred_bypass() -> None:
    import asyncio

    from app.services.agent.pipeline.runner import MessagePipeline

    async def run() -> None:
        from app.services.agent.harness.policy import MSG_TRANSFERRED

        r = await MessagePipeline(None).handle("你好", conversation_status="transferred")
        check(
            "L0/L2 transferred 状态不进入 AI",
            "transferred_skip_ai" in r.flags and r.answer == MSG_TRANSFERRED,
            f"route={r.route} answer={r.answer!r} flags={r.flags}",
        )

    asyncio.run(run())


def test_refusal_skips_llm() -> None:
    """Weak/zero evidence must not call the generator (LLM)."""
    import asyncio

    from app.services.rag.pipeline import RAGPipeline

    async def run() -> None:
        pipe = RAGPipeline()
        calls = {"n": 0}

        async def fake_generate(**kwargs):  # type: ignore[no-untyped-def]
            calls["n"] += 1
            return "SHOULD-NOT-BE-CALLED"

        pipe.generator.generate = fake_generate  # type: ignore[assignment]

        async def fake_retrieve(query, *, top_k, flags):  # type: ignore[no-untyped-def]
            return []  # zero hits → refusal

        pipe._retrieve_fused = fake_retrieve  # type: ignore[assignment]
        res = await pipe.run("今天月球天气如何量子纠缠")
        check(
            "L3 弱/零证据拒答不调用 LLM",
            res.refused and calls["n"] == 0,
            f"refused={res.refused} reason={res.refusal_reason} llm_calls={calls['n']}",
        )

    asyncio.run(run())


def test_documented_config_exists() -> None:
    s = get_settings()
    names = {
        "CONTEXT_MAX_TURNS": hasattr(s, "context_max_turns"),
        "CONTEXT_MAX_CHARS_PER_MSG": hasattr(s, "context_max_chars_per_msg"),
        "CONTEXT_MAX_TOTAL_CHARS": hasattr(s, "context_max_total_chars"),
        "RAG_MAX_CHUNKS": hasattr(s, "rag_max_chunks"),
        "RAG_MAX_CHARS_PER_CHUNK": hasattr(s, "rag_max_chars_per_chunk"),
    }
    ok = all(names.values())
    check(
        "文档旋钮与代码配置对齐",
        ok,
        f"{names}（实际复用 max_history_*，chunk 预算未见配置）",
    )


if __name__ == "__main__":
    for fn in [
        test_history_turn_window,
        test_history_char_budget,
        test_history_msg_truncation,
        test_staff_mirror,
        test_illegal_role_drop,
        test_system_role_leak,
        test_summary_compression,
        test_rewrite_coreference,
        test_grounding_threshold,
        test_context_assembler_trace,
        test_refusal_skips_llm,
        test_transferred_bypass,
        test_documented_config_exists,
    ]:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__, False, f"EXC {type(exc).__name__}: {exc}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("\n==== SUMMARY ====")
    print(f"passed={passed} failed={total - passed} total={total}")
