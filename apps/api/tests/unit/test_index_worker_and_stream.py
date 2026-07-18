"""Index worker process_job + generator token sink streaming."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import database as dbmod
from app.core.database import Base
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.services.knowledge.indexer.service import IndexerService
from app.services.knowledge.storage.local import LocalObjectStorage
from app.services.llm.client import ChatRequest, LLMClient
from app.services.rag.generator.service import AnswerGenerator
from app.services.rag.generator.token_sink import reset_token_sink, set_token_sink
from app.services.rag.vector.store import get_default_vector_store, reset_default_vector_store
from app.workers.index_worker.consumer import process_job
from app.workers.index_worker.queue import IndexJob

_HTTP_OK = 200


@pytest_asyncio.fixture
async def db_session(tmp_path):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    old_engine, old_session = dbmod.engine, dbmod.SessionLocal
    dbmod.engine = engine
    dbmod.SessionLocal = session_factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()
    dbmod.engine = old_engine
    dbmod.SessionLocal = old_session


@pytest.mark.asyncio
async def test_indexer_upserts_vector_chunks(db_session: AsyncSession, tmp_path):
    reset_default_vector_store()
    storage = LocalObjectStorage(root=str(tmp_path))
    raw = b"# Return policy\n\nSeven day return window with intact packaging.\n"
    key = "documents/test/return.md"
    storage.put(key, raw)
    doc = Document(
        title="退货",
        filename="return.md",
        content_type="text/markdown",
        status=DocumentStatus.PENDING.value,
        storage_key=key,
    )
    db_session.add(doc)
    await db_session.flush()

    out = await IndexerService(db_session, storage).index_document(doc.id, raw=raw)
    assert out.status == DocumentStatus.ACTIVE.value
    assert out.chunk_count >= 1

    store = get_default_vector_store()
    hits = await store.search("seven day return", top_k=3)
    assert hits
    assert any("return" in h.text.lower() or "退" in h.text for h in hits) or hits[0].score > 0


@pytest.mark.asyncio
async def test_process_job_indexes_pending_document(db_session: AsyncSession):
    """Worker uses default LocalObjectStorage — write into that root."""
    reset_default_vector_store()
    storage = LocalObjectStorage()
    raw = b"Invoice: electronic VAT invoices are supported after order completion.\n"
    doc = Document(
        title="发票",
        filename="invoice.md",
        content_type="text/markdown",
        status=DocumentStatus.PENDING.value,
    )
    db_session.add(doc)
    await db_session.flush()
    key = f"documents/{doc.id}/invoice.md"
    storage.put(key, raw)
    doc.storage_key = key
    await db_session.commit()

    result = await process_job(IndexJob(document_id=doc.id))
    assert "error" not in result, result
    assert result["status"] == DocumentStatus.ACTIVE.value
    assert result["chunk_count"] >= 1
    try:
        storage.delete(key)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_token_sink_receives_llm_stream_chunks():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body.get("stream") is True
        lines = [
            'data: {"choices":[{"delta":{"content":"A"}}]}\n',
            'data: {"choices":[{"delta":{"content":"B"}}]}\n',
            "data: [DONE]\n",
        ]
        return httpx.Response(_HTTP_OK, text="".join(lines))

    llm = LLMClient(
        base_url="http://llm.test",
        api_key="sk-test",
        transport=httpx.MockTransport(handler),
    )
    gen = AnswerGenerator(llm=llm)
    received: list[str] = []

    async def sink(chunk: str) -> None:
        received.append(chunk)

    token = set_token_sink(sink)
    try:
        answer = await gen.generate(
            question="q",
            sources=[{"index": 1, "text": "证据", "source": "s"}],
            messages=[{"role": "user", "content": "q"}],
        )
    finally:
        reset_token_sink(token)

    assert answer == "AB"
    assert received == ["A", "B"]


@pytest.mark.asyncio
async def test_token_sink_offline_chunks_extractive():
    gen = AnswerGenerator(llm=LLMClient(base_url=None, api_key=None))
    received: list[str] = []

    async def sink(chunk: str) -> None:
        received.append(chunk)

    token = set_token_sink(sink)
    try:
        answer = await gen.generate(
            question="q",
            sources=[{"index": 1, "text": "政策正文若干字保证超过步长", "source": "s"}],
            messages=None,
        )
    finally:
        reset_token_sink(token)

    assert "政策正文" in answer
    assert received
    assert "".join(received) == answer
