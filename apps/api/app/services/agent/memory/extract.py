"""Deterministic candidate-fact extraction from explicit user statements (arch §9.8)."""

import re

from app.services.agent.memory.facts import FactCandidate

MAX_PROPOSALS = 3

LANGUAGE_PATTERNS = (
    (re.compile(r"(用|请用|以后用)(英文|英语)", re.IGNORECASE), "preferred_language", "en-US"),
    (re.compile(r"(用|请用|以后用)(中文|汉语)", re.IGNORECASE), "preferred_language", "zh-CN"),
    (
        re.compile(r"\b(speak|reply|write|respond)\s+(to me\s+)?in\s+english\b", re.IGNORECASE),
        "preferred_language",
        "en-US",
    ),
    (
        re.compile(r"\b(speak|reply|write|respond)\s+(to me\s+)?in\s+(chinese|mandarin)\b", re.IGNORECASE),
        "preferred_language",
        "zh-CN",
    ),
)
CONTACT_PATTERNS = (
    (re.compile(r"(以后|请)?(用|通过)?邮件(联系|回复|通知|发)", re.IGNORECASE), "contact_channel", "email"),
    (re.compile(r"\b(email|e-mail)\s+me\b", re.IGNORECASE), "contact_channel", "email"),
    (re.compile(r"(以后|请)?(用|通过)?(电话|短信)(联系|回复|通知)", re.IGNORECASE), "contact_channel", "sms"),
    (re.compile(r"\b(text|call)\s+me\b", re.IGNORECASE), "contact_channel", "sms"),
)
ORDER_PATTERNS = (
    re.compile(r"(?:我的)?订单号?(?:是|为|:|：)?\s*([A-Z]{2,}\d{6,})", re.IGNORECASE),
    re.compile(r"\border\s+(?:id|number)?\s*(?:is|:)?\s*([A-Z]{2,}\d{6,})", re.IGNORECASE),
)


def extract_facts(text: str) -> list[FactCandidate]:
    """Only explicit user statements; the explicit turn itself is the confirmation."""
    proposals: list[FactCandidate] = []
    for pattern, key, value in (*LANGUAGE_PATTERNS, *CONTACT_PATTERNS):
        if len(proposals) >= MAX_PROPOSALS:
            break
        if pattern.search(text) and not any(p.key == key for p in proposals):
            proposals.append(_candidate(key, value))
    if len(proposals) < MAX_PROPOSALS:
        for pattern in ORDER_PATTERNS:
            match = pattern.search(text)
            if match:
                proposals.append(_candidate("last_order_id", match.group(1).upper()))
                break
    return proposals[:MAX_PROPOSALS]


def _candidate(key: str, value: str) -> FactCandidate:
    return FactCandidate(key=key, value=value, source="customer_stated", confirmed=True)
