"""Regression tests for the 2026-07-18 defect audit — business logic, RAG and plugins.

D-01 SLA first response, D-04 cost seeds, D-05/D-13 feature deltas, D-06 refuse handler,
D-07/D-19 fusion, D-08 encodings, D-09 notify-after-commit, D-11 index vs. transaction,
D-12 citations, D-14 vague queries, D-20 history cap.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.after_commit import on_commit
from app.core.config import Settings
from app.core.database import Base
from app.models.enums import HandoffStatus, Intent, TicketStatus
from app.models.handoff import HandoffSession
from app.models.ticket import Ticket
from app.plugins import runtime as plugin_context
from app.plugins.loader import load_plugins
from app.plugins.manifest import ManifestError, resolve_features
from app.services.agent.harness.policy import Harness
from app.services.agent.intent.classifier import IntentClassifier
from app.services.handoff.timeout import HandoffTimeoutSweeper
from app.services.knowledge.parser.parser import UnsupportedEncodingError, parse_bytes
from app.services.notify.service import clear_notify_sink, get_notify_sink
from app.services.rag.bm25.index import BM25Index
from app.services.rag.citations.verify import verify_citations
from app.services.rag.fusion.rrf import fuse_hits
from app.services.ticket.repository.service import TicketRepository
from app.services.ticket.sla.engine import SLAEngine


SECRET = "s" * 32
TOP_K = 3
STRONG, WEAK, MID = 0.95, 0.3, 0.7
OOB_CITATION = 9
HISTORY_CAP = 5
BOILERPLATE_REPEATS = 20


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


@dataclass
class Hit:
    doc_id: str
    text: str
    score: float
    source: str = "faq"
    meta: dict = field(default_factory=dict)


# --- D-01 -----------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_answered_ticket_does_not_breach_first_response(db: AsyncSession):
    ticket = Ticket(user_id="u", title="t", priority="high", conversation_id="c1")
    db.add(ticket)
    await db.flush()
    await TicketRepository(db).update_status(ticket, status=TicketStatus.PROCESSING.value)
    assert ticket.first_responded_at is not None
    later = datetime.now(UTC) + timedelta(hours=2)
    state, reason = SLAEngine(db).evaluate_ticket(ticket, later)
    assert reason != "first_response"


@pytest.mark.asyncio
async def test_staff_reply_stamps_first_response(db: AsyncSession):
    ticket = Ticket(user_id="u", title="t", priority="high", conversation_id="c2")
    db.add(ticket)
    await db.flush()
    await TicketRepository(db).mark_first_response("c2")
    await db.refresh(ticket)
    assert ticket.first_responded_at is not None


# --- D-05 / D-13 / D-06 ---------------------------------------------------------------------


def test_removing_a_required_plugin_is_an_error():
    with pytest.raises(ManifestError, match="still required by"):
        resolve_features("full", "-tools")


def test_typo_in_remove_delta_is_an_error():
    with pytest.raises(ManifestError, match="mcpp"):
        resolve_features("full", "-mcpp")


def test_remove_with_its_dependents_works():
    assert "mcp" not in resolve_features("full", "-mcp")


@pytest.mark.parametrize("profile", ["core-only", "faq-only"])
def test_every_profile_can_refuse(profile: str):
    previous = plugin_context.get_app_context()
    try:
        settings = Settings(ASKFLOW_ENV="test", SECRET_KEY=SECRET, ASKFLOW_PROFILE=profile)
        ctx = load_plugins(settings)
        assert {"refuse", "clarify"} <= set(ctx.route_handlers)
    finally:
        plugin_context.set_app_context(previous)


# --- D-07 / D-19 ----------------------------------------------------------------------------


def test_same_prefix_chunks_stay_distinct():
    prefix = "退货政策 " * BOILERPLATE_REPEATS
    hits = [Hit("d", prefix + "七天无理由", STRONG), Hit("d", prefix + "运费由买家承担", MID)]
    assert len(fuse_hits([hits, []], top_k=TOP_K)) == len(hits)


def test_strongest_absolute_hit_survives_rrf_cut():
    agreed = [Hit("a", f"common {i}", WEAK) for i in range(TOP_K)]
    strongest = Hit("b", "exact answer", STRONG)
    fused = fuse_hits([agreed, [*agreed, strongest]], top_k=TOP_K)
    assert fused[0].text == "exact answer"
    assert len(fused) == TOP_K


# --- D-08 -----------------------------------------------------------------------------------


def test_gbk_text_is_decoded():
    assert parse_bytes("退货须在七天内申请".encode("gbk"), filename="a.txt") == "退货须在七天内申请"


def test_utf16_and_bom_utf8_are_decoded():
    assert parse_bytes("发票".encode("utf-16"), filename="a.txt") == "发票"
    assert parse_bytes("\ufeff发票".encode(), filename="a.md") == "发票"


def test_undecodable_bytes_fail_loudly():
    with pytest.raises(UnsupportedEncodingError):
        parse_bytes(b"\x81\x20\xff\xfe\x00\x81", filename="a.txt")


# --- D-09 -----------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sweep_does_not_notify_until_published(db: AsyncSession):
    from app.models.conversation import Conversation

    conv = Conversation(user_id="u", title="c")
    db.add(conv)
    await db.flush()
    db.add(HandoffSession(conversation_id=conv.id, user_id="u", status=HandoffStatus.QUEUED.value))
    await db.flush()
    clear_notify_sink()
    sweeper = HandoffTimeoutSweeper(db)
    sweeper.settings = Settings(ASKFLOW_ENV="test", SECRET_KEY=SECRET, handoff_timeout_seconds=0)
    outcomes = await sweeper.sweep()
    assert len(outcomes) == 1
    assert get_notify_sink() == []
    await db.commit()
    await sweeper.publish(outcomes)
    assert [e["event"] for e in get_notify_sink()] == ["handoff.timeout"]


# --- D-11 -----------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_mutation_waits_for_commit(db: AsyncSession):
    index = BM25Index()
    # BM25 idf needs a background corpus to score a single matching chunk above zero
    index.add_documents([{"doc_id": f"bg{i}", "text": f"背景 资料 {i}"} for i in range(TOP_K)])
    await db.execute(text("select 1"))
    on_commit(db, lambda: index.replace_document("d1", [{"doc_id": "d1", "text": "回滚"}]))
    await db.rollback()
    await db.execute(text("select 1"))
    await db.commit()
    assert index.search("回滚") == []
    await db.execute(text("select 1"))
    on_commit(db, lambda: index.replace_document("d1", [{"doc_id": "d1", "text": "提交"}]))
    await db.commit()
    assert index.search("提交")[0].doc_id == "d1"


# --- D-12 / D-14 / D-20 ---------------------------------------------------------------------


def test_full_width_citations_are_checked():
    result = verify_citations(f"见【{OOB_CITATION}】与［1］", [{"index": 1}, {"index": 2}])
    assert result["result"] == "oob"
    assert result["oob"] == [OOB_CITATION]


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["在吗", "你好！", "hi?"])
async def test_vague_message_asks_to_clarify(text: str):
    result = await IntentClassifier().classify(text)
    assert result.intent == Intent.FAQ
    assert result.needs_clarify


@pytest.mark.asyncio
async def test_real_question_is_not_clarified():
    assert not (await IntentClassifier().classify("退货政策是什么")).needs_clarify


def test_history_cap_comes_from_settings():
    settings = Settings(ASKFLOW_ENV="test", SECRET_KEY=SECRET, max_history_msg_chars=HISTORY_CAP)
    flags: list[str] = []
    cleaned = Harness(settings)._sanitize_history([{"role": "user", "content": "一二三四五六七"}], flags)
    assert cleaned[0]["content"] == "一二三四五"
    assert "history_msg_truncated" in flags


@pytest.mark.asyncio
async def test_active_documents_are_rehydrated_on_boot(db: AsyncSession, tmp_path):
    from app.models.document import Document
    from app.models.enums import DocumentStatus
    from app.services.knowledge.indexer.service import rehydrate_index
    from app.services.knowledge.storage.local import LocalObjectStorage
    from app.services.rag.bm25.index import get_default_bm25, reset_default_bm25

    storage = LocalObjectStorage(tmp_path)
    storage.put("doc/kb.txt", "以旧换新活动每月一号开始，旧机最高抵扣八百元。".encode("gbk"))
    doc = Document(
        title="以旧换新",
        filename="kb.txt",
        status=DocumentStatus.ACTIVE.value,
        storage_key="doc/kb.txt",
    )
    db.add(doc)
    await db.flush()
    reset_default_bm25()  # simulate a fresh process: only the seed FAQ is indexed
    assert await rehydrate_index(db, storage) == 1
    assert get_default_bm25().search("以旧换新抵扣")[0].doc_id == doc.id
    reset_default_bm25()


def test_offline_answer_keeps_only_relevant_sentences():
    from app.services.rag.generator.extractive import extractive_answer

    sources = [
        {"index": 1, "text": "# 退换货政策\n7 天内可无理由退货。\n退款在验收后 3-5 个工作日原路返回。"},
        {"index": 2, "text": "每消费 1 元累计 1 积分，积分可抵现。"},
    ]
    answer = extractive_answer("退款多久到账", sources)
    assert "退款在验收后 3-5 个工作日原路返回。 [1]" in answer
    assert "积分" not in answer
    assert "#" not in answer
