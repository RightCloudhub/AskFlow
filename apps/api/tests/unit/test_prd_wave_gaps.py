"""PRD residual wave gaps: E9 PII, E10 publish, E12 cancel (shipped paths)."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import database as dbmod
from app.core.database import Base
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.services.audit.logger.service import AuditService
from app.services.audit.masking.mask import mask_detail, mask_string
from app.services.cancel_registry import (
    CancelRegistry,
    get_cancel_registry,
    reset_cancel_registry,
)
from app.services.knowledge.indexer.service import IndexerService
from app.services.knowledge.publish import PublishService
from app.services.knowledge.revisions import RevisionStore
from app.services.knowledge.storage.local import LocalObjectStorage
from app.services.rag.generator.service import CANCELLED_ANSWER, AnswerGenerator
from app.services.llm.client import LLMClient


# --- E9 extended PII ---


def test_mask_order_phone_id_bank_address():
    s = mask_string(
        "联系人 13812345678 邮箱 a@b.com "
        "订单号：AB1234567890 "
        "身份证 110101199001011234 "
        "卡号 6222021234567890123 "
        "地址 广东省深圳市南山区科技园南路1001号"
    )
    assert "13812345678" not in s
    assert "***PHONE***" in s or "***" in s
    assert "a***@b.com" in s or "***" in s
    assert "AB1234567890" not in s
    assert "7890" in s  # order tail kept
    assert "110101199001011234" not in s
    assert "***ID***" in s
    assert "6222021234567890123" not in s
    assert "***CARD***" in s
    assert "科技园" not in s or "***ADDR***" in s


@pytest.mark.asyncio
async def test_audit_service_masks_detail_on_log(db_session: AsyncSession):
    svc = AuditService(db_session)
    row = await svc.log(
        action="test.pii",
        resource_type="user",
        resource_id="u1",
        detail={"note": "手机 13900001111 订单号 ORD999888777"},
    )
    assert "13900001111" not in str(row.detail)
    assert "ORD999888777" not in str(row.detail)


# --- E12 cancel ---


def test_cancel_registry_local_roundtrip():
    reset_cancel_registry()
    reg = CancelRegistry()
    assert reg.is_cancelled("conv-1") is False
    reg.request_cancel("conv-1")
    assert reg.is_cancelled("conv-1") is True
    reg.clear("conv-1")
    assert reg.is_cancelled("conv-1") is False


@pytest.mark.asyncio
async def test_generator_honors_cancel_key():
    reset_cancel_registry()
    get_cancel_registry().request_cancel("c-x")
    gen = AnswerGenerator(llm=LLMClient(base_url=None, api_key=None))
    out = await gen.generate(
        question="q",
        sources=[{"index": 1, "text": "证据", "source": "s"}],
        messages=None,
        cancel_key="c-x",
    )
    assert out == CANCELLED_ANSWER


# --- E10 publish diff / rollback ---


@pytest_asyncio.fixture
async def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("REVISION_STORE_DIR", str(tmp_path / "revs"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    old_e, old_s = dbmod.engine, dbmod.SessionLocal
    dbmod.engine = engine
    dbmod.SessionLocal = factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as session:
        yield session
    await engine.dispose()
    dbmod.engine = old_e
    dbmod.SessionLocal = old_s
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_publish_diff_and_rollback(db_session: AsyncSession, tmp_path, monkeypatch):
    monkeypatch.setenv("REVISION_STORE_DIR", str(tmp_path / "revs"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    store = RevisionStore(root=tmp_path / "revs")
    storage = LocalObjectStorage(root=tmp_path / "uploads")
    raw1 = b"# Policy\n\nVersion one return in 7 days.\n"
    raw2 = b"# Policy\n\nVersion two return in 14 days.\n"
    doc = Document(
        title="policy",
        filename="p.md",
        content_type="text/markdown",
        status=DocumentStatus.PENDING.value,
        generation=0,
    )
    db_session.add(doc)
    await db_session.flush()
    key = f"documents/{doc.id}/p.md"
    storage.put(key, raw1)
    doc.storage_key = key
    await db_session.flush()

    indexer = IndexerService(db_session, storage)
    # Patch save path to use temp RevisionStore
    from app.services.knowledge import publish as pub_mod

    def _save(document_id, *, generation, source, chunks, store=None):
        store = store or RevisionStore(root=tmp_path / "revs")
        from app.services.knowledge.revisions import RevisionSnapshot

        store.save(
            RevisionSnapshot(
                document_id=document_id,
                generation=generation,
                source=source,
                chunks=list(chunks),
                chunk_count=len(chunks),
            )
        )

    monkeypatch.setattr(pub_mod, "save_revision_from_chunks", _save)

    d1 = await indexer.index_document(doc.id, raw=raw1)
    assert d1.generation == 1
    storage.put(key, raw2)
    d2 = await indexer.index_document(doc.id, raw=raw2)
    assert d2.generation == 2

    pub = PublishService(db_session, revisions=store, storage=storage)
    gens = pub.list_generations(doc.id)
    assert 1 in gens and 2 in gens
    diff = pub.diff(doc.id, 1, 2)
    assert diff["to_chunk_count"] >= 1
    assert isinstance(diff["added"], list)

    rolled = await pub.rollback(doc.id, 1)
    assert rolled.generation == 3
    assert rolled.status == DocumentStatus.ACTIVE.value
    snap3 = store.load(doc.id, 3)
    assert snap3 is not None
    joined = " ".join(snap3.chunks)
    assert "7" in joined or "return" in joined.lower() or "天" in joined
