"""Optional rerank stage between fusion and grounding (arch §4.7)."""

from app.services.rag.rerank.reranker import LexicalReranker, apply_rerank

__all__ = ["LexicalReranker", "apply_rerank"]
