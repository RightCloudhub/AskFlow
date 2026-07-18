"""PII / secret masking for audit detail (PRD §4.11)."""

from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\-\s]{8,}\d)")
TOKEN_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*")
# PRC resident ID: 17 digits + check digit (0-9/X)
ID_CARD_RE = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")
# Payment cards: 16–19 consecutive digits (avoid shorter order-ish numbers)
BANK_CARD_RE = re.compile(r"(?<!\d)(\d{16,19})(?!\d)")
PASSWORD_KEYS = frozenset({"password", "passwd", "secret", "token", "api_key", "authorization"})
ID_MASK = "***ID***"
BANK_MASK = "***CARD***"
PHONE_MASK = "***PHONE***"


def mask_string(value: str) -> str:
    s = EMAIL_RE.sub(lambda m: _mask_email(m.group(0)), value)
    s = TOKEN_RE.sub(r"\1***", s)
    s = ID_CARD_RE.sub(ID_MASK, s)
    s = BANK_CARD_RE.sub(BANK_MASK, s)
    s = PHONE_RE.sub(PHONE_MASK, s)
    return s


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    keep = local[:1] if local else "*"
    return f"{keep}***@{domain}"


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
