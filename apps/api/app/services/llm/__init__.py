"""OpenAI-compatible LLM client (optional; offline extractive fallback elsewhere)."""

from app.services.llm.client import ChatRequest, LLMClient, get_llm_client, reset_llm_client

__all__ = ["ChatRequest", "LLMClient", "get_llm_client", "reset_llm_client"]
