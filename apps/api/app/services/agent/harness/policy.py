"""Cognitive Harness — hard input/route/output guards (PRD §4.3.3).

Security copy and thresholds are CODE CONSTANTS — not prompt templates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings
from app.models.enums import LEGAL_ROUTES, Route

# --- Hard-coded user-facing copy (must not live in prompt tables) ---
MSG_EMPTY = "请输入您的问题，我会尽力帮助您。"
MSG_TOO_LONG = "问题过长，请精简到 2000 字以内后再试。"
MSG_INJECTION = "抱歉，我无法执行该请求。请直接描述您的业务问题。"
MSG_EMPTY_OUTPUT = "抱歉，暂时无法生成有效回答，请稍后再试或转人工。"
MSG_TRUNCATED_SUFFIX = "\n\n…（回答过长已截断，如需更多细节请继续追问）"
MSG_CLARIFY = "我还不太确定您的具体需求，能否补充更多细节？例如：订单号、产品名称或具体故障现象。"
MSG_TRANSFERRED = "当前会话已转人工，客服接入后会回复您。"
MSG_OUT_OF_SCOPE = (
    "该问题超出本客服助手的业务范围，我无法提供医疗诊断、法律代理意见或与产品无关的臆测性回答。"
    "请就本产品的订单、账号、物流或功能问题提问，或转人工处理。"
)

INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
        r"disregard\s+(all\s+)?(previous|prior)\s+",
        r"you\s+are\s+now\s+(dan|jailbreak|unrestricted)",
        r"system\s*prompt",
        r"reveal\s+(your\s+)?(system|hidden)\s+prompt",
        r"忽略(以上|之前|前面)?(所有)?(指令|规则|提示)",
        r"无视(所有)?(系统)?(提示|指令)",
        r"越狱",
        r"jailbreak",
        r"pretend\s+you\s+have\s+no\s+restrictions",
        r"developer\s+mode\s+enabled",
    ]
]


@dataclass
class PrepareResult:
    allowed: bool
    text: str
    history: list[dict[str, str]] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    stop_message: str | None = None
    reason: str | None = None


@dataclass
class RouteDecision:
    route: Route
    forced: bool = False
    reason: str | None = None
    flags: list[str] = field(default_factory=list)


@dataclass
class FinalizeResult:
    text: str
    flags: list[str] = field(default_factory=list)
    truncated: bool = False


class Harness:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def policy_version(self) -> str:
        return self.settings.harness_policy_version

    def prepare(
        self,
        text: str,
        history: list[dict[str, Any]] | None = None,
    ) -> PrepareResult:
        flags: list[str] = []
        raw = (text or "").strip()
        if not raw:
            return PrepareResult(
                allowed=False,
                text="",
                stop_message=MSG_EMPTY,
                reason="empty",
                flags=["block_empty"],
            )
        if len(raw) > self.settings.max_question_chars:
            return PrepareResult(
                allowed=False,
                text=raw[: self.settings.max_question_chars],
                stop_message=MSG_TOO_LONG,
                reason="too_long",
                flags=["block_too_long"],
            )
        if self._looks_like_injection(raw):
            return PrepareResult(
                allowed=False,
                text=raw,
                stop_message=MSG_INJECTION,
                reason="injection",
                flags=["block_injection"],
            )

        cleaned_history = self._sanitize_history(history or [], flags)
        from app.services.agent.history_summary import compress_history

        cleaned_history, compressed = compress_history(
            cleaned_history, settings=self.settings
        )
        if compressed:
            flags.append("history_summarized")
        return PrepareResult(allowed=True, text=raw, history=cleaned_history, flags=flags)

    def choose_route(
        self,
        route: str | Route | None,
        *,
        confidence: float,
        needs_clarify: bool = False,
    ) -> RouteDecision:
        flags: list[str] = []
        if needs_clarify or confidence < self.settings.intent_clarify_threshold:
            return RouteDecision(
                route=Route.CLARIFY,
                forced=True,
                reason="low_confidence",
                flags=["force_clarify"],
            )

        candidate: Route | None
        if isinstance(route, Route):
            candidate = route
        elif isinstance(route, str):
            try:
                candidate = Route(route)
            except ValueError:
                candidate = None
        else:
            candidate = None

        if candidate is None or candidate not in LEGAL_ROUTES:
            flags.append("illegal_route")
            return RouteDecision(
                route=Route.RAG,
                forced=True,
                reason="illegal_route",
                flags=flags,
            )
        return RouteDecision(route=candidate, forced=False, flags=flags)

    def finalize(self, text: str | None) -> FinalizeResult:
        body = (text or "").strip()
        flags: list[str] = []
        if not body:
            return FinalizeResult(text=MSG_EMPTY_OUTPUT, flags=["empty_output"])
        max_chars = self.settings.max_answer_chars
        if len(body) > max_chars:
            truncated = body[:max_chars].rstrip() + MSG_TRUNCATED_SUFFIX
            return FinalizeResult(text=truncated, flags=["truncated"], truncated=True)
        return FinalizeResult(text=body, flags=flags)

    def clarify_message(self) -> str:
        return MSG_CLARIFY

    def transferred_message(self) -> str:
        return MSG_TRANSFERRED

    def out_of_scope_message(self) -> str:
        return MSG_OUT_OF_SCOPE

    def _looks_like_injection(self, text: str) -> bool:
        return any(p.search(text) for p in INJECTION_PATTERNS)

    def _sanitize_history(
        self,
        history: list[dict[str, Any]],
        flags: list[str],
    ) -> list[dict[str, str]]:
        """Keep recent turns; mirror staff → assistant; drop illegal roles."""
        cleaned: list[dict[str, str]] = []
        for item in history:
            role = str(item.get("role", "")).lower()
            content = str(item.get("content", "") or "")
            if role == "staff":
                role = "assistant"
                flags.append("staff_mirrored")
            if role not in {"user", "assistant", "system"}:
                flags.append("dropped_illegal_role")
                continue
            if len(content) > 2000:
                content = content[:2000]
                flags.append("history_msg_truncated")
            cleaned.append({"role": role, "content": content})

        max_msgs = self.settings.max_history_messages
        if len(cleaned) > max_msgs:
            cleaned = cleaned[-max_msgs:]
            flags.append("history_truncated")

        # char budget from the end
        budget = self.settings.max_history_chars
        acc: list[dict[str, str]] = []
        used = 0
        for msg in reversed(cleaned):
            n = len(msg["content"])
            if used + n > budget and acc:
                flags.append("history_char_budget")
                break
            acc.append(msg)
            used += n
        acc.reverse()
        return acc
