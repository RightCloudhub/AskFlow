"""Keyed identifiers, authenticated encryption and RFC 6238 TOTP."""

import base64
import hashlib
import hmac
import secrets
import struct
import time

from cryptography.fernet import Fernet

from app.core.config import get_settings

TOTP_PERIOD = 30
TOTP_DIGITS = 6
TOTP_MODULUS = 10 ** TOTP_DIGITS
TOTP_SECRET_BYTES = 20
TOTP_OFFSET_MASK = 15
TOTP_VALUE_MASK = 0x7FFFFFFF
TOTP_INTEGER_BYTES = 4
RECOVERY_CODE_COUNT = 10
RECOVERY_TOKEN_BYTES = 12


def digest(value: str) -> str:
    key = get_settings().mall_refresh_secret.encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def vault() -> Fernet:
    key = hashlib.sha256(get_settings().mall_totp_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(value: str) -> str:
    return vault().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return vault().decrypt(value.encode()).decode() if value else ""


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(TOTP_SECRET_BYTES)).decode()


def totp(secret: str, step: int) -> str:
    mac = hmac.new(base64.b32decode(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = mac[-1] & TOTP_OFFSET_MASK
    value = struct.unpack(">I", mac[offset:offset + TOTP_INTEGER_BYTES])[0] & TOTP_VALUE_MASK
    return str(value % TOTP_MODULUS).zfill(TOTP_DIGITS)


def matched_step(secret: str, code: str, *, now: float | None = None) -> int | None:
    current = int((time.time() if now is None else now) // TOTP_PERIOD)
    for offset in (-1, 0, 1):
        step = current + offset
        if step >= 0 and hmac.compare_digest(totp(secret, step), code):
            return step
    return None
