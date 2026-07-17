"""Production OIDC path: real JWKS-validated RS256 tokens (no live IdP)."""

from __future__ import annotations

import time
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.services.auth.jwks import JWKSValidator
from app.services.auth.oidc import OIDCService

ISSUER = "https://idp.example.test"
AUDIENCE = "askflow-client"
KID = "test-key-1"


def _rsa_pair() -> tuple[Any, dict[str, Any], bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()

    def _b64int(n: int) -> str:
        import base64

        length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(length, "big")).decode("ascii").rstrip("=")

    jwk = {
        "kty": "RSA",
        "kid": KID,
        "use": "sig",
        "alg": "RS256",
        "n": _b64int(public_numbers.n),
        "e": _b64int(public_numbers.e),
    }
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return private_key, jwk, pem


def _sign(claims: dict[str, Any], pem: bytes, *, kid: str = KID) -> str:
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


@pytest.fixture
def rsa_material():
    return _rsa_pair()


@pytest.fixture
def prod_settings() -> Settings:
    return Settings(
        ASKFLOW_ENV="staging",
        SECRET_KEY="test-secret-key-not-for-prod-xx",
        OIDC_ISSUER=ISSUER,
        OIDC_CLIENT_ID=AUDIENCE,
        OIDC_MOCK=False,
    )


def test_jwks_validator_accepts_valid_token(rsa_material):
    _priv, jwk, pem = rsa_material
    now = int(time.time())
    token = _sign(
        {
            "sub": "u-1",
            "email": "a@corp.test",
            "preferred_username": "alice",
            "roles": ["admin"],
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": now + 600,
            "iat": now,
        },
        pem,
    )
    v = JWKSValidator(issuer=ISSUER, audience=AUDIENCE, jwks_override={"keys": [jwk]})
    claims = v.verify_id_token(token)
    assert claims["sub"] == "u-1"
    assert claims["email"] == "a@corp.test"


def test_jwks_rejects_bad_signature(rsa_material):
    _priv, jwk, pem = rsa_material
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    now = int(time.time())
    token = _sign(
        {
            "sub": "u-2",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": now + 600,
            "iat": now,
        },
        other_pem,
    )
    v = JWKSValidator(issuer=ISSUER, audience=AUDIENCE, jwks_override={"keys": [jwk]})
    with pytest.raises(ValueError, match="invalid_signature|invalid_claims"):
        v.verify_id_token(token)


def test_jwks_rejects_expired(rsa_material):
    _priv, jwk, pem = rsa_material
    now = int(time.time())
    token = _sign(
        {
            "sub": "u-3",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": now - 30,
            "iat": now - 120,
        },
        pem,
    )
    v = JWKSValidator(issuer=ISSUER, audience=AUDIENCE, jwks_override={"keys": [jwk]})
    with pytest.raises(ValueError, match="token_expired"):
        v.verify_id_token(token)


def test_jwks_rejects_wrong_audience(rsa_material):
    _priv, jwk, pem = rsa_material
    now = int(time.time())
    token = _sign(
        {
            "sub": "u-4",
            "iss": ISSUER,
            "aud": "other-client",
            "exp": now + 600,
            "iat": now,
        },
        pem,
    )
    v = JWKSValidator(issuer=ISSUER, audience=AUDIENCE, jwks_override={"keys": [jwk]})
    with pytest.raises(ValueError, match="invalid_claims"):
        v.verify_id_token(token)


@pytest.mark.asyncio
async def test_oidc_login_production_path_with_jwks(rsa_material, prod_settings):
    _priv, jwk, pem = rsa_material
    now = int(time.time())
    token = _sign(
        {
            "sub": "oidc-prod-1",
            "email": "prod@corp.test",
            "preferred_username": "prod_user",
            "roles": ["agent"],
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": now + 600,
            "iat": now,
        },
        pem,
    )
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        svc = OIDCService(
            db,
            settings=prod_settings,
            jwks_override={"keys": [jwk]},
        )
        tok, user = await svc.login_with_id_token(token)
        assert tok.access_token
        assert user.email == "prod@corp.test"
        assert user.role == "agent"

        with pytest.raises(ValueError):
            await svc.login_with_id_token("not-a-jwt")
    await engine.dispose()


@pytest.mark.asyncio
async def test_oidc_mock_path_still_works_in_test_env():
    from app.services.auth.oidc import encode_mock_id_token

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        settings = Settings(
            ASKFLOW_ENV="test",
            SECRET_KEY="test-secret-key-not-for-prod-xx",
        )
        token = encode_mock_id_token(
            {
                "sub": "m1",
                "email": "mock@corp.test",
                "preferred_username": "mocky",
                "roles": ["user"],
            }
        )
        tok, user = await OIDCService(db, settings=settings).login_with_id_token(token)
        assert tok.access_token
        assert user.role == "user"
    await engine.dispose()
