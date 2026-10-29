"""Bounded TTL LRU, Redis L2, explicit off and per-key single flight."""

import asyncio
import json
import random
import time
from collections import OrderedDict

from app.commerce.infra.metrics import CACHE_TOTAL


class MemoryCache:
    def __init__(self, max_entries: int):
        self.max_entries, self.entries = max_entries, OrderedDict()

    async def get(self, key: str):
        item = self.entries.get(key)
        if item is None:
            return False, None
        expires, value = item
        if expires <= time.monotonic():
            self.entries.pop(key, None)
            return False, None
        self.entries.move_to_end(key)
        return True, value

    async def put(self, key: str, value, *, ttl: int):
        self.entries[key] = (time.monotonic() + ttl, value)
        self.entries.move_to_end(key)
        while len(self.entries) > self.max_entries:
            self.entries.popitem(last=False)

    async def delete(self, key: str):
        self.entries.pop(key, None)


class OffCache:
    async def get(self, key: str):
        return False, None

    async def put(self, key: str, value, *, ttl: int):
        return None

    async def delete(self, key: str):
        return None


class RedisCache:
    def __init__(self, connection):
        self.connection = connection

    async def get(self, key: str):
        data = await self.connection.client().get("mall:cache:" + key)
        return (False, None) if data is None else (True, json.loads(data))

    async def put(self, key: str, value, *, ttl: int):
        await self.connection.client().set("mall:cache:" + key, json.dumps(value), ex=ttl)

    async def delete(self, key: str):
        await self.connection.client().incr("mall:cache-version:" + key)
        await self.connection.client().delete("mall:cache:" + key)

    async def version(self, key: str):
        return await self.connection.client().get("mall:cache-version:" + key) or "0"


class CachedReads:
    def __init__(self, backend, settings):
        self.backend, self.settings = backend, settings
        self.l1 = MemoryCache(settings.cache_max_entries)
        self.shards = [asyncio.Lock() for _ in range(settings.lock_shards)]

    async def get(self, key: str, loader):
        if isinstance(self.backend, OffCache):
            return await loader()
        if isinstance(self.backend, RedisCache):
            try:
                key += ":generation:" + str(await self.backend.version(key))
            except Exception:
                CACHE_TOTAL.labels(result="degraded").inc()
                return await loader()
        hit, value = await self.l1.get(key)
        if hit:
            CACHE_TOTAL.labels(result="hit").inc()
            return value
        async with self.shards[hash(key) % len(self.shards)]:
            hit, value = await self._load_cache(key)
            if hit:
                return value
            value = await loader()
            ttl = self.settings.cache_ttl_seconds if value else self.settings.cache_null_ttl_seconds
            ttl += random.randint(0, self.settings.cache_jitter_seconds)
            await self.l1.put(key, value, ttl=ttl)
            try:
                await self.backend.put(key, value, ttl=ttl)
            except Exception:
                CACHE_TOTAL.labels(result="degraded").inc()
            CACHE_TOTAL.labels(result="miss").inc()
            return value

    async def _load_cache(self, key):
        hit, value = await self.l1.get(key)
        if hit:
            return hit, value
        try:
            hit, value = await self.backend.get(key)
        except Exception:
            return False, None
        if hit:
            await self.l1.put(key, value, ttl=self.settings.cache_null_ttl_seconds)
            CACHE_TOTAL.labels(result="hit").inc()
        return hit, value

    async def delete(self, key):
        await self.l1.delete(key)
        await self.backend.delete(key)
