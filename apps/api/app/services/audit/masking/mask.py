"""PII / secret masking for audit detail (PRD §4.11 / E9 extended)."""

from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\-\s]{8,}\d)")
TOKEN_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*")
# PRC resident ID: 17 digits + check digit (0-9/X)
ID_CARD_RE = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")
# Payment cards: 16–19 consecutive digits
BANK_CARD_RE = re.compile(r"(?<!\d)(\d{16,19})(?!\d)")
# Order ids: labeled or bare alphanumeric order-like tokens
ORDER_LABELED_RE = re.compile(
    r"(?i)((?:订单|order)(?:号|编号|id)?\s*[:：#]?\s*)([A-Za-z0-9\-_]{6,})"
)
# Bare order-like tokens with alpha prefix (avoid pure digit bank/phone collisions)
ORDER_BARE_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2,}\d{6,})(?![A-Za-z0-9])")
# Rough CN address: province/city/district markers + street residual
ADDRESS_RE = re.compile(
    r"([\u4e00-\u9fff]{2,12}(?:省|市|自治区|特别行政区)"
    r"[\u4e00-\u9fff0-9\-号楼室单元层]{4,40})"
)
PASSWORD_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "authorization",
        "id_card",
        "bank_card",
        "ssn",
    }
)

ID_MASK = "***ID***"
BANK_MASK = "***CARD***"
PHONE_MASK = "***PHONE***"
ADDRESS_MASK = "***ADDR***"
ORDER_KEEP_TAIL = 4


def mask_string(value: str) -> str:
    s = EMAIL_RE.sub(lambda m: _mask_email(m.group(0)), value)
    s = TOKEN_RE.sub(r"\1***", s)
    s = ID_CARD_RE.sub(ID_MASK, s)
    s = BANK_CARD_RE.sub(BANK_MASK, s)
    s = ORDER_LABELED_RE.sub(_mask_order_labeled, s)
    s = ORDER_BARE_RE.sub(lambda m: _mask_order_id(m.group(1)), s)
    s = ADDRESS_RE.sub(ADDRESS_MASK, s)
    s = PHONE_RE.sub(PHONE_MASK, s)
    return s


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    keep = local[:1] if local else "*"
    return f"{keep}***@{domain}"


def _mask_order_id(order_id: str) -> str:
    if len(order_id) <= ORDER_KEEP_TAIL:
        return "***"
    return f"***{order_id[-ORDER_KEEP_TAIL:]}"


def _mask_order_labeled(match: re.Match[str]) -> str:
    return f"{match.group(1)}{_mask_order_id(match.group(2))}"


def mask_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    if not detail:
        return {}
    return _walk(detail)  # type: ignore[return-value]


def _walk(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if str(k).lower() in PASSWORD_KEYS:
                out[k] = "***"
            else:
                out[k] = _walk(v)
        return out
    if isinstance(obj, list):
        return [_walk(x) for x in obj]
    if isinstance(obj, str):
        return mask_string(obj)
    return obj
