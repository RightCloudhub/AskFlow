"""OIDC ID token validation against issuer JWKS (injectable for tests)."""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx
from jose import JWTError, jwk, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

JWKS_CACHE_TTL_SEC = 3600
ALLOWED_ALGS = ("RS256",)
HTTP_TIMEOUT_SEC = 10.0

FetchFn = Callable[[str], dict[str, Any]]


class JWKSValidator:
    """Fetch/cache JWKS and verify signed OIDC ID tokens."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        fetch_jwks: FetchFn | None = None,
        jwks_override: dict[str, Any] | None = None,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self._fetch = fetch_jwks or self._default_fetch
        self._override = jwks_override
        self._now = now_fn or time.time
        self._cached: dict[str, Any] | None = None
        self._cached_at: float = 0.0

    def _default_fetch(self, issuer: str) -> dict[str, Any]:
        discovery_url = f"{issuer}/.well-known/openid-configuration"
        with httpx.Client(timeout=HTTP_TIMEOUT_SEC) as client:
            disc = client.get(discovery_url)
            disc.raise_for_status()
            jwks_uri = disc.json().get("jwks_uri")
            if not jwks_uri:
                raise ValueError("oidc_jwks_uri_missing")
            resp = client.get(jwks_uri)
            resp.raise_for_status()
            return resp.json()

    def get_jwks(self) -> dict[str, Any]:
        if self._override is not None:
            return self._override
        now = self._now()
        if self._cached is not None and (now - self._cached_at) < JWKS_CACHE_TTL_SEC:
            return self._cached
        data = self._fetch(self.issuer)
        self._cached = data
        self._cached_at = now
        return data

    def verify_id_token(self, id_token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(id_token)
        except JWTError as exc:
            raise ValueError("invalid_token_header") from exc
        kid = header.get("kid")
        alg = header.get("alg") or "RS256"
        if alg not in ALLOWED_ALGS:
            raise ValueError("unsupported_alg")
        key = self._select_key(kid)
        try:
            return jwt.decode(
                id_token,
                key,
                algorithms=list(ALLOWED_ALGS),
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_at_hash": False},
            )
        except ExpiredSignatureError as exc:
            raise ValueError("token_expired") from exc
        except JWTClaimsError as exc:
            raise ValueError("invalid_claims") from exc
        except JWTError as exc:
            raise ValueError("invalid_signature") from exc

    def _select_key(self, kid: str | None) -> Any:
        jwks = self.get_jwks()
        keys = jwks.get("keys") or []
        if not keys:
            raise ValueError("jwks_empty")
        chosen = None
        if kid:
            for k in keys:
                if k.get("kid") == kid:
                    chosen = k
                    break
            if chosen is None:
                raise ValueError("kid_not_found")
        else:
            chosen = keys[0]
        return jwk.construct(chosen)
