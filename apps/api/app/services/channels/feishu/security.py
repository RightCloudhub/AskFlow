"""Feishu (Lark) webhook authentication: signature, replay window, nonce cache, decryption (D-10).

With ``FEISHU_ENCRYPT_KEY`` set, every event must carry
``X-Lark-Signature = sha256(timestamp + nonce + encrypt_key + raw_body)``, a timestamp inside
``REPLAY_WINDOW_SEC`` and a nonce not seen before. The one exception is the URL-verification
handshake, which Feishu sends unsigned; it is accepted only with the verification token.
Staging/production refuse every event when the encrypt key is not configured.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.core.config import Settings

REPLAY_WINDOW_SEC = 300
AES_BLOCK_BITS = 128
IV_BYTES = 16
URL_VERIFICATION = "url_verification"


class FeishuAuthError(Exception):
    """Raised with a short reason code; the route maps it to HTTP 403."""


@dataclass
class NonceCache:
    """Nonces seen inside the replay window (single process; Redis for multi-worker)."""

    seen: dict[str, float] = field(default_factory=dict)

    def claim(self, nonce: str, now: float) -> None:
        self.seen = {n: t for n, t in self.seen.items() if now - t <= REPLAY_WINDOW_SEC}
        if nonce in self.seen:
            raise FeishuAuthError("replayed_nonce")
        self.seen[nonce] = now


_NONCES = NonceCache()


def decrypt_body(encrypted: str, encrypt_key: str) -> dict[str, Any]:
    raw = base64.b64decode(encrypted)
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    decryptor = Cipher(algorithms.AES(key), modes.CBC(raw[:IV_BYTES])).decryptor()
    padded = decryptor.update(raw[IV_BYTES:]) + decryptor.finalize()
    unpadder = padding.PKCS7(AES_BLOCK_BITS).unpadder()
    return json.loads(unpadder.update(padded) + unpadder.finalize())


def token_matches(body: dict[str, Any], expected: str | None) -> bool:
    token = body.get("token") or body.get("header", {}).get("token") or ""
    return bool(expected) and hmac.compare_digest(str(token), expected)


@dataclass
class FeishuRequest:
    raw_body: bytes
    headers: dict[str, str]

    def expected_signature(self, encrypt_key: str) -> str:
        timestamp = self.headers.get("x-lark-request-timestamp", "")
        nonce = self.headers.get("x-lark-request-nonce", "")
        material = (timestamp + nonce + encrypt_key).encode("utf-8") + self.raw_body
        return hashlib.sha256(material).hexdigest()


def authenticate(request: FeishuRequest, settings: Settings) -> dict[str, Any]:
    """Return the verified (and decrypted) event body or raise ``FeishuAuthError``."""
    key = settings.feishu_encrypt_key
    if not key:
        return _token_only(request, settings)
    body = json.loads(request.raw_body)
    if "encrypt" in body:
        body = decrypt_body(body["encrypt"], key)
    signature = request.headers.get("x-lark-signature")
    if signature is None and body.get("type") == URL_VERIFICATION:
        _require_token(body, settings)
        return body
    _verify_signature(request, key, signature or "")
    _require_token(body, settings)
    return body


def _token_only(request: FeishuRequest, settings: Settings) -> dict[str, Any]:
    if settings.is_production_like:
        raise FeishuAuthError("encrypt_key_required")
    body = json.loads(request.raw_body)
    if settings.feishu_verification_token:
        _require_token(body, settings)
    return body


def _require_token(body: dict[str, Any], settings: Settings) -> None:
    if not token_matches(body, settings.feishu_verification_token):
        raise FeishuAuthError("bad_token")


def _verify_signature(request: FeishuRequest, key: str, signature: str) -> None:
    timestamp = request.headers.get("x-lark-request-timestamp", "")
    nonce = request.headers.get("x-lark-request-nonce", "")
    now = time.time()
    if not timestamp.isdigit() or abs(now - int(timestamp)) > REPLAY_WINDOW_SEC:
        raise FeishuAuthError("stale_timestamp")
    if not hmac.compare_digest(signature, request.expected_signature(key)):
        raise FeishuAuthError("bad_signature")
    _NONCES.claim(nonce, now)
