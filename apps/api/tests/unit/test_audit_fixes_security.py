"""Regression tests for the 2026-07-18 defect audit — auth, transport and channel security.

D-02 OIDC linking, D-03/D-16/D-17 rate limiting, D-10 Feishu webhook, D-18 /metrics.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.requests import Request

from app.core.config import Settings
from app.core.database import Base
from app.core.security import hash_password
from app.middleware import rate_limit
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth.oidc import OIDCService, encode_mock_id_token, map_roles
from app.services.channels.feishu import security as feishu

SECRET = "test-secret-key-not-for-prod-xx"
ENCRYPT_KEY = "lark-encrypt-key"
VERIFY_TOKEN = "vt-1"
SHA256_HEX_LEN = 64


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


async def _local_admin(db: AsyncSession) -> User:
    user = User(
        username="boss",
        email="boss@corp.com",
        hashed_password=hash_password("password123"),
        role=UserRole.ADMIN.value,
    )
    db.add(user)
    await db.flush()
    return user


def _token(**claims: object) -> str:
    return encode_mock_id_token({"sub": "idp-1", "email": "boss@corp.com", **claims})


# --- D-02 -----------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unverified_email_never_takes_over_existing_account(db: AsyncSession):
    await _local_admin(db)
    with pytest.raises(ValueError, match="email_not_verified"):
        await OIDCService(db).login_with_id_token(_token(roles=["admin"]))


@pytest.mark.asyncio
async def test_verified_email_links_once_then_sub_is_the_identity(db: AsyncSession):
    admin = await _local_admin(db)
    await OIDCService(db).login_with_id_token(_token(email_verified=True, roles=["admin"]))
    assert admin.oidc_subject == "idp-1"
    # Same sub with a changed e-mail still resolves to the bound account
    _, out = await OIDCService(db).login_with_id_token(
        _token(email="renamed@corp.com", roles=["admin"])
    )
    assert out.id == admin.id


@pytest.mark.asyncio
async def test_role_change_from_idp_is_audited(db: AsyncSession):
    admin = await _local_admin(db)
    await OIDCService(db).login_with_id_token(_token(email_verified=True, roles=["user"]))
    assert admin.role == UserRole.USER.value
    rows = (await db.execute(select(AuditLog.action, AuditLog.detail))).all()
    assert ("auth.sso_role_changed", {"from": "admin", "to": "user"}) in [tuple(r) for r in rows]


def test_group_path_suffix_no_longer_grants_admin():
    assert map_roles(["/evil/admin"]) == UserRole.USER.value
    assert map_roles(["/admin"]) == UserRole.ADMIN.value


# --- D-03 / D-16 / D-17 ---------------------------------------------------------------------


def _request(xff: str, peer: str = "10.0.0.9") -> Request:
    headers = [(b"x-forwarded-for", xff.encode())]
    return Request({"type": "http", "headers": headers, "client": (peer, 1), "path": "/"})


def _settings(monkeypatch: pytest.MonkeyPatch, **extra: object) -> None:
    values = {"trust_proxy_headers": True, "trusted_proxy_hops": 1, **extra}
    monkeypatch.setattr(rate_limit, "get_settings", lambda: SimpleNamespace(**values))


def test_spoofed_leftmost_xff_is_ignored(monkeypatch: pytest.MonkeyPatch):
    _settings(monkeypatch)
    assert rate_limit.client_ip(_request("6.6.6.6, 203.0.113.7")) == "203.0.113.7"
    assert rate_limit.client_ip(_request("1.1.1.1, 203.0.113.7")) == "203.0.113.7"


def test_two_proxy_hops_read_second_from_right(monkeypatch: pytest.MonkeyPatch):
    _settings(monkeypatch, trusted_proxy_hops=2)
    assert rate_limit.client_ip(_request("6.6.6.6, 203.0.113.7, 10.1.1.1")) == "203.0.113.7"


def test_xff_ignored_without_trust(monkeypatch: pytest.MonkeyPatch):
    _settings(monkeypatch, trust_proxy_headers=False)
    assert rate_limit.client_ip(_request("6.6.6.6")) == "10.0.0.9"


def test_skip_list_is_exact_and_idle_keys_are_evicted(monkeypatch: pytest.MonkeyPatch):
    _settings(monkeypatch, api_prefix="/api/v1")
    mw = rate_limit.RateLimitMiddleware(app=None)
    assert "/api/v1/health" in mw._skip
    assert "/api/v1/admin/reports/metrics" not in mw._skip
    mw._hits["old"].append(time.time() - 2 * rate_limit.WINDOW_SEC)
    mw._last_sweep = 0
    mw._sweep(time.time())
    assert "old" not in mw._hits


# --- D-18 -----------------------------------------------------------------------------------


def test_production_refuses_to_start_without_metrics_token():
    with pytest.raises(RuntimeError, match="METRICS_TOKEN"):
        Settings(ASKFLOW_ENV="production", SECRET_KEY=SECRET).assert_startup_safe()
    Settings(ASKFLOW_ENV="production", SECRET_KEY=SECRET, METRICS_TOKEN="m").assert_startup_safe()


# --- D-10 -----------------------------------------------------------------------------------


def _lark_settings() -> Settings:
    return Settings(
        ASKFLOW_ENV="production",
        SECRET_KEY=SECRET,
        FEISHU_ENCRYPT_KEY=ENCRYPT_KEY,
        FEISHU_VERIFICATION_TOKEN=VERIFY_TOKEN,
    )


def _signed(body: dict, *, nonce: str, ts: int | None = None) -> feishu.FeishuRequest:
    raw = json.dumps(body).encode()
    stamp = str(ts if ts is not None else int(time.time()))
    material = (stamp + nonce + ENCRYPT_KEY).encode() + raw
    headers = {
        "x-lark-request-timestamp": stamp,
        "x-lark-request-nonce": nonce,
        "x-lark-signature": hashlib.sha256(material).hexdigest(),
    }
    return feishu.FeishuRequest(raw, headers)


EVENT = {"token": VERIFY_TOKEN, "header": {"event_type": "im.message.receive_v1"}}


def test_valid_signature_passes_and_replay_is_rejected():
    request = _signed(EVENT, nonce="n-replay")
    assert feishu.authenticate(request, _lark_settings())["token"] == VERIFY_TOKEN
    with pytest.raises(feishu.FeishuAuthError, match="replayed_nonce"):
        feishu.authenticate(request, _lark_settings())


def test_forged_signature_and_stale_timestamp_are_rejected():
    forged = _signed(EVENT, nonce="n-forged")
    forged.headers["x-lark-signature"] = "0" * SHA256_HEX_LEN
    with pytest.raises(feishu.FeishuAuthError, match="bad_signature"):
        feishu.authenticate(forged, _lark_settings())
    stale = _signed(EVENT, nonce="n-stale", ts=int(time.time()) - 2 * feishu.REPLAY_WINDOW_SEC)
    with pytest.raises(feishu.FeishuAuthError, match="stale_timestamp"):
        feishu.authenticate(stale, _lark_settings())


def test_unsigned_url_verification_needs_the_token():
    ok = feishu.FeishuRequest(
        json.dumps({"type": "url_verification", "challenge": "c", "token": VERIFY_TOKEN}).encode(),
        {},
    )
    assert feishu.authenticate(ok, _lark_settings())["challenge"] == "c"
    bad = feishu.FeishuRequest(b'{"type": "url_verification", "token": "nope"}', {})
    with pytest.raises(feishu.FeishuAuthError, match="bad_token"):
        feishu.authenticate(bad, _lark_settings())


def test_encrypted_body_is_decrypted():
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    iv = b"0123456789abcdef"
    padder = padding.PKCS7(feishu.AES_BLOCK_BITS).padder()
    plain = padder.update(json.dumps(EVENT).encode()) + padder.finalize()
    key = hashlib.sha256(ENCRYPT_KEY.encode()).digest()
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    blob = iv + enc.update(plain) + enc.finalize()
    request = _signed({"encrypt": base64.b64encode(blob).decode()}, nonce="n-enc")
    assert feishu.authenticate(request, _lark_settings())["header"] == EVENT["header"]
