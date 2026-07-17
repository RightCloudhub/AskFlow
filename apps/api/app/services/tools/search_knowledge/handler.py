"""search_knowledge tool — wraps BM25 index."""

from __future__ import annotations

from typing import Any

from app.services.rag.bm25.index import get_default_bm25


async def search_knowledge(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query") or "").strip()
    top_k = int(arguments.get("top_k") or 5)
    if not query:
        return {"status": "ok", "items": []}
    try:
        hits = get_default_bm25().search(query, top_k=top_k)
        return {
            "status": "ok",
            "items": [
                {
                    "title": h.source,
                    "source": h.source,
                    "content": h.text,
                    "score": h.score,
                }
                for h in hits
            ],
        }
    except Exception:
        return {"status": "ok", "items": []}
