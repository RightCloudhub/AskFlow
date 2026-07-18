"""Vector channel, offline embedding, LLM generate, and index worker."""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.llm.client import ChatRequest, LLMClient
from app.services.rag.embedding.client import OfflineEmbedder, OpenAIEmbedder
from app.services.rag.generator.service import AnswerGenerator
from app.services.rag.pipeline import RAGPipeline
from app.services.rag.vector.memory import MemoryVectorIndex, cosine_similarity
from app.services.rag.vector.store import VectorStore, ensure_seeded, reset_default_vector_store
from app.services.rag.vector.types import VectorRecord
from app.workers.index_worker.queue import IndexJob, IndexQueue, reset_index_queue

_OFFLINE_DIM_SMALL = 64
_OFFLINE_DIM = 128
_WEAK_SCORE_MAX = 0.55
_L2_TOL = 1e-6
_HTTP_OK = 200
_DEQUEUE_TIMEOUT_SEC = 0.5
_DEQUEUE_EMPTY_SEC = 0.1
_TOP_K = 3
_MOCK_EMB_SCALE = 0.1
_MOCK_EMB_Y = 0.2
_MOCK_EMB_Z = 0.3


@pytest.mark.asyncio
async def test_offline_embedder_is_deterministic():
    emb = OfflineEmbedder(dim=_OFFLINE_DIM_SMALL)
    a = await emb.embed(["退货政策七天无理由"])
    b = await emb.embed(["退货政策七天无理由"])
    assert a[0] == b[0]
    assert abs(sum(x * x for x in a[0]) - 1.0) < _L2_TOL


@pytest.mark.asyncio
async def test_memory_vector_search_ranks_related_higher():
    emb = OfflineEmbedder(dim=_OFFLINE_DIM)
    mem = MemoryVectorIndex()
    texts = [
        ("d1", "退货政策：签收七天内可退货，包装完整。"),
        ("d2", "物流配送默认顺丰，满99包邮。"),
    ]
    vecs = await emb.embed([t[1] for t in texts])
    mem.upsert(
        [
            VectorRecord(
                id=f"{doc_id}:0",
                doc_id=doc_id,
                source=doc_id,
                text=text,
                embedding=vec,
                meta={"chunk_index": 0},
            )
            for (doc_id, text), vec in zip(texts, vecs, strict=True)
        ]
    )
    qv = (await emb.embed(["退货怎么退"]))[0]
    hits = mem.search(qv, top_k=2)
    assert hits
    assert hits[0].doc_id == "d1"
    assert hits[0].score > hits[-1].score or len(hits) == 1


@pytest.mark.asyncio
async def test_vector_store_search_after_seed():
    reset_default_vector_store()
    store = VectorStore(embedder=OfflineEmbedder(dim=_OFFLINE_DIM), memory=MemoryVectorIndex())
    await ensure_seeded(store)
    hits = await store.search("退货政策是什么", top_k=_TOP_K)
    assert hits
    assert hits[0].score > 0
    weak = await store.search("今天月球天气如何量子纠缠", top_k=_TOP_K)
    if weak:
        assert weak[0].score < _WEAK_SCORE_MAX


@pytest.mark.asyncio
async def test_openai_embedder_mock_http():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        n = len(body["input"])
        return httpx.Response(
            _HTTP_OK,
            json={
                "data": [
                    {
                        "index": i,
                        "embedding": [
                            _MOCK_EMB_SCALE * (i + 1),
                            _MOCK_EMB_Y,
                            _MOCK_EMB_Z,
                        ],
                    }
                    for i in range(n)
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    emb = OpenAIEmbedder(
        base_url="http://llm.test",
        api_key="sk-test",
        model="text-embedding-3-small",
        transport=transport,
    )
    out = await emb.embed(["a", "b"])
    assert len(out) == 2
    assert out[0][0] == pytest.approx(_MOCK_EMB_SCALE)


@pytest.mark.asyncio
async def test_llm_client_complete_and_stream():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        if body.get("stream"):
            lines = [
                'data: {"choices":[{"delta":{"content":"你"}}]}\n',
                'data: {"choices":[{"delta":{"content":"好"}}]}\n',
                "data: [DONE]\n",
            ]
            return httpx.Response(_HTTP_OK, text="".join(lines))
        return httpx.Response(
            _HTTP_OK,
            json={"choices": [{"message": {"content": "完整回答 [1]"}}]},
        )

    transport = httpx.MockTransport(handler)
    client = LLMClient(base_url="http://llm.test", api_key="sk-test", transport=transport)
    assert client.available
    text = await client.complete(
        ChatRequest(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}])
    )
    assert "完整回答" in text
    tokens: list[str] = []
    async for t in client.stream(
        ChatRequest(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}], stream=True)
    ):
        tokens.append(t)
    assert "".join(tokens) == "你好"


@pytest.mark.asyncio
async def test_answer_generator_llm_path():
    def handler(request: httpx.Request) -> httpx.Response:
        # generate() streams under the hood for live token sink support
        lines = [
            'data: {"choices":[{"delta":{"content":"依据证据：七天可退"}}]}\n',
            'data: {"choices":[{"delta":{"content":" [1]"}}]}\n',
            "data: [DONE]\n",
        ]
        return httpx.Response(_HTTP_OK, text="".join(lines))

    llm = LLMClient(
        base_url="http://llm.test",
        api_key="sk-test",
        transport=httpx.MockTransport(handler),
    )
    gen = AnswerGenerator(llm=llm)
    answer = await gen.generate(
        question="退货？",
        sources=[{"index": 1, "text": "七天可退", "source": "a"}],
        messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "退货？"},
        ],
    )
    assert "七天可退" in answer
    assert "根据知识库资料" not in answer


@pytest.mark.asyncio
async def test_answer_generator_offline_extractive():
    gen = AnswerGenerator(llm=LLMClient(base_url=None, api_key=None))
    answer = await gen.generate(
        question="q",
        sources=[{"index": 1, "text": "政策正文", "source": "a"}],
        messages=None,
    )
    assert "根据知识库资料" in answer
    assert "政策正文" in answer


@pytest.mark.asyncio
async def test_rag_still_faq_and_refuse_with_real_vector():
    reset_default_vector_store()
    result = await RAGPipeline().run("退货政策是什么")
    assert result.refused is False
    assert result.sources
    refused = await RAGPipeline().run("今天月球天气如何量子纠缠")
    assert refused.refused is True


@pytest.mark.asyncio
async def test_index_queue_roundtrip():
    reset_index_queue()
    q = IndexQueue()
    await q.enqueue(IndexJob(document_id="doc-1"))
    job = await q.dequeue(timeout=_DEQUEUE_TIMEOUT_SEC)
    assert job is not None
    assert job.document_id == "doc-1"
    assert await q.dequeue(timeout=_DEQUEUE_EMPTY_SEC) is None


def test_cosine_identical_is_one():
    v = [0.0, 1.0, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)
