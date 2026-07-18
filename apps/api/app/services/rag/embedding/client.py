"""Text embedding: OpenAI-compatible HTTP + deterministic offline hash (PRD §4.2)."""

from __future__ import annotations

import hashlib
import math
import re
import time
from typing import Protocol, runtime_checkable

import httpx

from app.core.config import Settings, get_settings
from app.middleware.metrics import EMBEDDING_LATENCY, EMBEDDING_REQUESTS

# Offline hashing embedder defaults
DEFAULT_OFFLINE_DIM = 384
_HASH_MOD = 2**31 - 1
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+")

# HTTP
EMBED_TIMEOUT_SEC = 30.0
EMBED_PATH = "/v1/embeddings"


@runtime_checkable
class Embedder(Protocol):
    """Minimal embedding interface used by vector store / indexer."""

    @property
    def model(self) -> str: ...

    @property
    def dim(self) -> int: ...

    @property
    def backend(self) -> str: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


def _tokenize(text: str) -> list[str]:
    lower = (text or "").lower()
    tokens = _TOKEN_RE.findall(lower)
    return tokens or ([lower] if lower else [])


def _hash_token(token: str, dim: int) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % dim


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0:
        return vec
    return [v / norm for v in vec]


class OfflineEmbedder:
    """Hashing-trick bag-of-tokens → fixed dim. Deterministic, no network."""

    def __init__(self, dim: int = DEFAULT_OFFLINE_DIM, model: str = "offline-hash") -> None:
        self._dim = dim
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def backend(self) -> str:
        return "offline"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        started = time.perf_counter()
        try:
            out = [self._one(t) for t in texts]
            EMBEDDING_REQUESTS.labels(status="ok", backend=self.backend).inc()
            return out
        except Exception:
            EMBEDDING_REQUESTS.labels(status="error", backend=self.backend).inc()
            raise
        finally:
            EMBEDDING_LATENCY.labels(backend=self.backend).observe(time.perf_counter() - started)

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        tokens = _tokenize(text)
        if not tokens:
            return vec
        for tok in tokens:
            idx = _hash_token(tok, self._dim)
            # signed hash for better collision behavior
            sign = 1.0 if (_hash_token(tok + "#", _HASH_MOD) % 2 == 0) else -1.0
            vec[idx] += sign
        return _l2_normalize(vec)


class OpenAIEmbedder:
    """OpenAI-compatible POST /v1/embeddings via httpx."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        dim: int | None = None,
        timeout: float = EMBED_TIMEOUT_SEC,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._dim = dim
        self._timeout = timeout
        self._transport = transport

    @property
    def model(self) -> str:
        return self._model

    @property
    def dim(self) -> int:
        return self._dim or DEFAULT_OFFLINE_DIM

    @property
    def backend(self) -> str:
        return "openai"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        started = time.perf_counter()
        try:
            vectors = await self._request(texts)
            EMBEDDING_REQUESTS.labels(status="ok", backend=self.backend).inc()
            return vectors
        except Exception:
            EMBEDDING_REQUESTS.labels(status="error", backend=self.backend).inc()
            raise
        finally:
            EMBEDDING_LATENCY.labels(backend=self.backend).observe(time.perf_counter() - started)

    async def _request(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self._model, "input": texts}
        async with httpx.AsyncClient(
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            resp = await client.post(
                f"{self._base_url}{EMBED_PATH}",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        items = sorted(data.get("data") or [], key=lambda x: int(x.get("index", 0)))
        vectors = [list(map(float, item["embedding"])) for item in items]
        if vectors and self._dim is None:
            self._dim = len(vectors[0])
        return vectors


def settings_embedder(settings: Settings | None = None) -> Embedder:
    """Pick OpenAI embedder when configured; else offline."""
    s = settings or get_settings()
    base = s.embedding_base_url or s.llm_base_url
    key = s.embedding_api_key or s.llm_api_key
    if base and key:
        return OpenAIEmbedder(
            base_url=base,
            api_key=key,
            model=s.embedding_model,
            dim=s.embedding_dim,
            timeout=s.llm_timeout_seconds,
        )
    return OfflineEmbedder(dim=s.embedding_dim, model="offline-hash")
