"""OIDC SSO with role mapping (PRD E5 / §12.2).

Production: validate ID token against issuer JWKS.
Tests/dev: accept unsigned mock tokens when OIDC_MOCK=1 or env=test|development.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import TokenResponse, UserOut
from app.services.audit.logger.service import AuditService
from app.services.auth.jwks import JWKSValidator
from app.utils.ids import new_id

MOCK_ENVS = frozenset({"test", "development"})
B64_PAD_MOD = 4
USERNAME_MAX_LEN = 64


@dataclass
class OIDCClaims:
    sub: str
    email: str
    email_verified: bool
    preferred_username: str
    roles: list[str]


DEFAULT_ROLE_MAP = {
    "admin": UserRole.ADMIN.value,
    "administrator": UserRole.ADMIN.value,
    "agent": UserRole.AGENT.value,
    "support": UserRole.AGENT.value,
    "user": UserRole.USER.value,
}


def map_roles(raw_roles: list[str], role_map: dict[str, str] | None = None) -> str:
    mapping = role_map or DEFAULT_ROLE_MAP
    ranked = [UserRole.ADMIN.value, UserRole.AGENT.value, UserRole.USER.value]
    found: set[str] = set()
    for r in raw_roles:
        key = r.lower().strip("/")
        if key in mapping:
            found.add(mapping[key])
    for role in ranked:
        if role in found:
            return role
    return UserRole.USER.value


def decode_mock_id_token(token: str) -> dict[str, Any]:
    """Decode base64url(JSON) mock ID token used in tests."""
    pad = "=" * (-len(token) % B64_PAD_MOD)
    raw = base64.urlsafe_b64decode(token + pad)
    return json.loads(raw.decode("utf-8"))


def encode_mock_id_token(claims: dict[str, Any]) -> str:
    raw = json.dumps(claims, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def claims_from_payload(data: dict[str, Any]) -> OIDCClaims:
    roles = data.get("roles") or data.get("groups") or []
    if isinstance(roles, str):
        roles = [roles]
    sub = str(data["sub"])
    email = str(data.get("email") or f"{sub}@sso.local")
    username = str(data.get("preferred_username") or data.get("name") or email.split("@")[0])
    return OIDCClaims(
        sub=sub,
        email=email,
        email_verified=data.get("email_verified") is True,
        preferred_username=username[:USERNAME_MAX_LEN],
        roles=[str(r) for r in roles],
    )


class OIDCService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
        *,
        jwks_validator: JWKSValidator | None = None,
        jwks_fetch: Callable[[str], dict[str, Any]] | None = None,
        jwks_override: dict[str, Any] | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self._jwks_validator = jwks_validator
        self._jwks_fetch = jwks_fetch
        self._jwks_override = jwks_override

    def _use_mock(self) -> bool:
        # Never mock in staging/production (startup also refuses OIDC_MOCK there).
        if self.settings.is_production_like:
            return False
        # Tests: always mock for convenience (JWKS tests pass explicit staging Settings).
        if self.settings.env == "test":
            return True
        # development: require explicit OIDC_MOCK=1 (unsigned tokens are unsafe on open nets)
        return bool(self.settings.oidc_mock)

    def _validator(self) -> JWKSValidator:
        if self._jwks_validator is not None:
            return self._jwks_validator
        issuer = self.settings.oidc_issuer
        audience = self.settings.oidc_client_id
        if not issuer or not audience:
            raise ValueError("oidc_not_configured")
        return JWKSValidator(
            issuer=issuer,
            audience=audience,
            fetch_jwks=self._jwks_fetch,
            jwks_override=self._jwks_override,
        )

    def parse_id_token(self, id_token: str) -> OIDCClaims:
        if self._use_mock():
            try:
                data = decode_mock_id_token(id_token)
            except Exception as exc:
                raise ValueError("invalid_mock_token") from exc
            return claims_from_payload(data)

        if not self.settings.oidc_issuer or not self.settings.oidc_client_id:
            raise ValueError("oidc_not_configured")
        data = self._validator().verify_id_token(id_token)
        return claims_from_payload(data)

    async def login_with_id_token(self, id_token: str) -> tuple[TokenResponse, UserOut]:
        from app.commerce.account.sessions import legacy_token_extra

        user = await self.resolve_identity(id_token)
        extra = await legacy_token_extra(self.db, user.id)
        token = create_access_token(user.id, role=user.role,
            extra={"sso": True, "sub_oidc": user.oidc_subject, **extra})
        return TokenResponse(access_token=token), UserOut.model_validate(user)

    async def resolve_identity(self, id_token: str) -> User:
        claims = self.parse_id_token(id_token)
        role = map_roles(claims.roles)
        user = await self._resolve_user(claims, role)
        if not user.is_active:
            raise ValueError("user_disabled")
        await self._sync_role(user, role)
        return user

    async def _resolve_user(self, claims: OIDCClaims, role: str) -> User:
        """Find the account bound to ``sub``; link by email only when the IdP verified it."""
        bound = await self._first(User.oidc_subject == claims.sub)
        if bound is not None:
            return bound
        by_email = await self._first(User.email == claims.email)
        if by_email is None:
            return await self._create(claims, role)
        if not claims.email_verified:
            raise ValueError("email_not_verified")
        by_email.oidc_subject = claims.sub
        await AuditService(self.db).log(
            action="auth.sso_linked",
            resource_type="user",
            resource_id=by_email.id,
            actor_id=by_email.id,
            detail={"sub": claims.sub},
        )
        return by_email

    async def _first(self, condition: Any) -> User | None:
        result = await self.db.execute(select(User).where(condition))
        return result.scalar_one_or_none()

    async def _create(self, claims: OIDCClaims, role: str) -> User:
        user = User(
            username=claims.preferred_username,
            email=claims.email,
            hashed_password=hash_password(new_id() + "sso"),
            role=role,
            oidc_subject=claims.sub,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def _sync_role(self, user: User, role: str) -> None:
        """IdP groups are the source of truth for SSO accounts; every change is audited."""
        if user.role == role:
            return
        await AuditService(self.db).log(
            action="auth.sso_role_changed",
            resource_type="user",
            resource_id=user.id,
            actor_id=user.id,
            detail={"from": user.role, "to": role},
        )
        user.role = role
        await self.db.flush()
