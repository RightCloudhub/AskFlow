"""Cache only irreversible revocations; active sessions always consult the database."""

import logging
import time
from typing import Protocol

from sqlalchemy import select

from app.commerce.account.crypto import digest
from app.commerce.account.models import AccessRevocation, UserSession
from app.commerce.infra.cache import MemoryCache, RedisCache
from app.commerce.infra.errors import dependency_errors
from app.commerce.infra.runtime import infra
from app.core.config import get_settings
from app.plugins.runtime import require_app_context

logger = logging.getLogger("askflow.mall.sessions")


class RevocationStore(Protocol):
    async def revoked(self, db, claims: dict) -> bool: ...


class DatabaseRevocations:
    def __init__(self, cache):
        self.cache = cache

    async def revoked(self, db, claims: dict) -> bool:
        key = "revoked:" + digest(str(claims.get("jti", "")) + ":" + str(claims.get("sid", "")))
        try:
            hit, value = await self.cache.get(key)
            if hit and value:
                return True
        except dependency_errors():
            logger.warning("revocation cache unavailable; using database")
        revoked = await self.database_revoked(db, claims)
        if revoked:
            await self.remember(key, claims)
        return revoked

    async def remember(self, key: str, claims: dict):
        ttl = max(1, int(claims.get("exp", time.time()) - time.time()))
        try:
            await self.cache.put(key, True, ttl=ttl)
        except dependency_errors():
            logger.warning("revocation cache unavailable; using database")

    @staticmethod
    async def database_revoked(db, claims: dict) -> bool:
        if claims.get("jti") and await db.scalar(select(AccessRevocation.id).where(
            AccessRevocation.jti == claims["jti"])):
            return True
        if not claims.get("sid"):
            return False
        return bool(await db.scalar(select(UserSession.id).where(UserSession.id == claims["sid"],
            UserSession.user_id == claims.get("sub"), UserSession.revoked_at.is_not(None))))


class RedisRevocations(DatabaseRevocations):
    def __init__(self):
        super().__init__(RedisCache(infra().redis))


def store() -> RevocationStore:
    ctx, settings = require_app_context(), get_settings()
    if "mall_revocations" not in ctx.services:
        ctx.services["mall_revocations"] = RedisRevocations() if settings.session_backend == "redis" else (
            DatabaseRevocations(MemoryCache(settings.cache_max_entries)))
    return ctx.services["mall_revocations"]
