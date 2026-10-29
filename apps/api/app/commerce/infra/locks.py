"""Fenced Redis locks with renewal, sharded memory locks and PG advisory locks."""

import asyncio
import hashlib
from contextlib import asynccontextmanager
from http import HTTPStatus
from uuid import uuid4

from sqlalchemy import text

from app.commerce.core.errors import MallError
from app.commerce.infra.errors import dependency_errors
from app.core import database

MILLISECONDS = 1000
RENEW_DIVISOR = 3
HASH_BYTES = 8
ACQUIRE = """
if redis.call('exists', KEYS[1]) == 1 then return 0 end
local fence = redis.call('incr', KEYS[2])
redis.call('psetex', KEYS[1], ARGV[2], ARGV[1])
return fence
"""
RENEW = """
if redis.call('get', KEYS[1]) ~= ARGV[1] then return 0 end
return redis.call('pexpire', KEYS[1], ARGV[2])
"""
RELEASE = """
if redis.call('get', KEYS[1]) ~= ARGV[1] then return 0 end
return redis.call('del', KEYS[1])
"""


class MemoryLocks:
    def __init__(self, shards: int):
        self.shards = [asyncio.Lock() for _ in range(shards)]

    @asynccontextmanager
    async def hold(self, key):
        async with self.shards[hash(key) % len(self.shards)]:
            yield 0


class RedisLocks:
    def __init__(self, connection, settings):
        self.connection, self.ttl = connection, settings.lock_ttl_seconds

    @asynccontextmanager
    async def hold(self, key):
        client, owner = self.connection.client(), str(uuid4())
        name = "mall:lock:" + key
        fence = await client.eval(ACQUIRE, 2, name, name + ":fence", owner, self.ttl * MILLISECONDS)
        if not fence:
            raise MallError("resource_busy", status=HTTPStatus.TOO_MANY_REQUESTS)
        lost = asyncio.Event()
        renewer = asyncio.create_task(self._renew(name, owner, lost))
        try:
            yield int(fence)
            if lost.is_set():
                raise MallError("lock_lease_lost")
        finally:
            renewer.cancel()
            try:
                await renewer
            except asyncio.CancelledError:
                pass
            await client.eval(RELEASE, 1, name, owner)

    async def _renew(self, name, owner, lost):
        while True:
            await asyncio.sleep(self.ttl / RENEW_DIVISOR)
            try:
                result = await self.connection.client().eval(
                    RENEW, 1, name, owner, self.ttl * MILLISECONDS)
            except dependency_errors():
                lost.set()
                return
            if not result:
                lost.set()
                return


class PostgresLocks:
    @asynccontextmanager
    async def hold(self, key):
        digest = hashlib.sha256(key.encode()).digest()[:HASH_BYTES]
        value = int.from_bytes(digest, "big", signed=True)
        async with database.engine.connect() as connection:
            acquired = await connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": value})
            if not acquired:
                raise MallError("resource_busy", status=HTTPStatus.TOO_MANY_REQUESTS)
            try:
                yield 0
            finally:
                await connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": value})
