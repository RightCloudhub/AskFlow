"""Intent classification: rules first, optional LLM second (PRD §4.3.1)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.enums import Intent

# Rule patterns with medium confidence (0.7)
RULE_PATTERNS: list[tuple[Intent, re.Pattern[str], float]] = [
    (
        Intent.ORDER_QUERY,
        re.compile(
            r"(订单|快递|物流|发货|运单|到哪了|order|shipping|tracking|物流状态|单号)",
            re.I,
        ),
        0.7,
    ),
    (
        Intent.FAULT_REPORT,
        re.compile(r"(报错|错误码?|bug|故障|crash|崩溃|500|打不开|无法使用|异常)", re.I),
        0.7,
    ),
    (
        Intent.COMPLAINT,
        re.compile(r"(投诉|差评|不满|抱怨|complain|太差|坑|欺诈)", re.I),
        0.7,
    ),
]

# Handoff requires co-occurrence of human-request + transfer verbs (PRD red-line)
HANDOFF_HUMAN = re.compile(r"(人工|真人|客服|坐席|专员|human|agent\s*service|live\s*agent)", re.I)
HANDOFF_TRANSFER = re.compile(r"(转|找|接入|联系|talk\s*to|speak\s*(to|with)|connect|transfer)", re.I)
# Bare "agent" alone must NOT trigger handoff
BARE_AGENT = re.compile(r"\bagent\b", re.I)

# Domain out-of-scope (enterprise E4) — medical/legal/crypto gambling etc.
OUT_OF_SCOPE_RE = re.compile(
    r"(诊断|开药|处方|癌症治疗方案|法律意见|代写诉状|炒币建议|内幕交易|"
    r"how\s+to\s+(hack|make\s+a\s+bomb)|medical\s+diagnosis|legal\s+advice\s+for\s+court|"
    r"月球天气|量子纠缠天气预报|外星签证)",
    re.I,
)


@dataclass
class IntentResult:
    intent: Intent
    confidence: float
    source: str  # rule | llm | fallback
    needs_clarify: bool = False
    reasons: list[str] | None = None


class IntentClassifier:
    """MVP: rule-based; LLM hook is optional when client is configured."""

    def __init__(self, llm_client: object | None = None) -> None:
        self.llm_client = llm_client

    async def classify(self, text: str, history: list[dict[str, str]] | None = None) -> IntentResult:
        _ = history  # reserved for LLM path
        rule = self._rule_classify(text)

        if self.llm_client is not None:
            try:
                llm = await self._llm_classify(text)  # type: ignore[misc]
                if llm is not None:
                    if llm.confidence >= rule.confidence:
                        return llm
            except Exception:
                # best-effort: fall through to rules
                pass

        if rule.confidence < 0.5 and rule.intent == Intent.FAQ:
            return IntentResult(
                intent=Intent.FAQ,
                confidence=rule.confidence,
                source=rule.source,
                needs_clarify=False,
                reasons=rule.reasons,
            )
        return rule

    def _rule_classify(self, text: str) -> IntentResult:
        reasons: list[str] = []

        if OUT_OF_SCOPE_RE.search(text):
            return IntentResult(
                intent=Intent.OUT_OF_SCOPE,
                confidence=0.9,
                source="rule",
                reasons=["rule:out_of_scope"],
            )

        # Handoff: require co-occurrence — never bare "agent"
        if HANDOFF_HUMAN.search(text) and HANDOFF_TRANSFER.search(text):
            reasons.append("handoff_cooccurrence")
            return IntentResult(
                intent=Intent.HANDOFF,
                confidence=0.85,
                source="rule",
                reasons=reasons,
            )
        if BARE_AGENT.search(text) and not HANDOFF_HUMAN.search(text):
            reasons.append("bare_agent_ignored")

        best: IntentResult | None = None
        for intent, pattern, conf in RULE_PATTERNS:
            if pattern.search(text):
                candidate = IntentResult(
                    intent=intent,
                    confidence=conf,
                    source="rule",
                    reasons=[f"rule:{intent.value}"],
                )
                if best is None or candidate.confidence > best.confidence:
                    best = candidate

        if best is not None:
            best.reasons = (best.reasons or []) + reasons
            return best

        return IntentResult(
            intent=Intent.FAQ,
            confidence=0.55,
            source="fallback",
            reasons=reasons + ["default_faq"],
        )

    async def _llm_classify(self, text: str) -> IntentResult | None:
        """Placeholder for OpenAI-compatible structured classify."""
        _ = text
        return None
