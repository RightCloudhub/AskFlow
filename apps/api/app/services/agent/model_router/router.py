"""Purpose → model chain with fallback (PRD §4.14 / §12.2)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from app.core.config import Settings, get_settings
from app.middleware.metrics import LLM_ERROR_TOTAL, LLM_FALLBACK_TOTAL
from app.models.enums import LLMPurpose

T = TypeVar("T")


@dataclass
class ModelSelection:
    purpose: str
    model: str
    base_url: str | None
    api_key: str | None
    fallbacks: list[str]


class ModelRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def pick(self, purpose: LLMPurpose | str) -> ModelSelection:
        p = purpose.value if isinstance(purpose, LLMPurpose) else purpose
        mapping = {
            LLMPurpose.INTENT_CLASSIFY.value: self.settings.llm_model_classify,
            LLMPurpose.QUERY_REWRITE.value: self.settings.llm_model_rewrite,
            LLMPurpose.RAG_GENERATE.value: self.settings.llm_model_generate,
            LLMPurpose.HANDOFF_SUMMARY.value: self.settings.llm_model_summary,
            LLMPurpose.GAP_DRAFT_ASSIST.value: self.settings.llm_model_summary,
            LLMPurpose.EMBEDDING.value: self.settings.embedding_model,
        }
        primary = mapping.get(p, self.settings.llm_model_generate)
        fallbacks: list[str] = []
        for m in (
            self.settings.llm_model_classify,
            self.settings.llm_model_summary,
            "gpt-4o-mini",
            "gpt-3.5-turbo",
        ):
            if m != primary and m not in fallbacks:
                fallbacks.append(m)
        if not fallbacks:
            fallbacks = [f"{primary}-fallback"]

        if p == LLMPurpose.EMBEDDING.value:
            return ModelSelection(
                purpose=p,
                model=primary,
                base_url=self.settings.embedding_base_url or self.settings.llm_base_url,
                api_key=self.settings.embedding_api_key or self.settings.llm_api_key,
                fallbacks=[],
            )

        return ModelSelection(
            purpose=p,
            model=primary,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            fallbacks=fallbacks,
        )

    async def call_with_fallback(
        self,
        purpose: LLMPurpose | str,
        invoker: Callable[[str], Awaitable[T]],
        *,
        primary_override: str | None = None,
        force_primary_fail: bool = False,
    ) -> tuple[T, dict[str, Any]]:
        """Invoke invoker(model); on failure walk fallback chain.

        force_primary_fail: test hook to exercise fallback without real network.
        """
        sel = self.pick(purpose)
        chain = [primary_override or sel.model, *sel.fallbacks]
        # de-dupe preserve order
        seen: set[str] = set()
        models: list[str] = []
        for m in chain:
            if m not in seen:
                seen.add(m)
                models.append(m)

        last_err: Exception | None = None
        for i, model in enumerate(models):
            try:
                if force_primary_fail and i == 0:
                    raise RuntimeError("simulated_primary_failure")
                result = await invoker(model)
                meta = {
                    "purpose": sel.purpose,
                    "model": model,
                    "attempt": i + 1,
                    "fallback_used": i > 0,
                    "chain": models,
                }
                if i > 0:
                    LLM_FALLBACK_TOTAL.labels(
                        purpose=sel.purpose,
                        from_model=models[0],
                        to_model=model,
                    ).inc()
                return result, meta
            except Exception as exc:
                last_err = exc
                LLM_ERROR_TOTAL.labels(
                    purpose=sel.purpose,
                    error_class=type(exc).__name__,
                ).inc()
                continue
        raise RuntimeError(f"all_models_failed:{sel.purpose}:{last_err}")
