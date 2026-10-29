"""Atomic Redis and bounded process sliding-window rate limiters."""

import asyncio
import time
from collections import OrderedDict, deque
from uuid import uuid4

MAX_BUCKETS = 20_000
MILLISECONDS = 1000
WINDOW_LUA = """
redis.call('zremrangebyscore', KEYS[1], '-inf', ARGV[1]-ARGV[2])
if redis.call('zcard', KEYS[1]) >= tonumber(ARGV[3]) then return 0 end
redis.call('zadd', KEYS[1], ARGV[1], ARGV[4])
redis.call('pexpire', KEYS[1], ARGV[2])
return 1
"""


class MemoryLimits:
    def __init__(self):
        self.hits, self.lock = OrderedDict(), asyncio.Lock()

    async def allow(self, key: str, *, limit: int, window: int):
        async with self.lock:
            now = time.monotonic()
            self._evict(now, window=window)
            if key not in self.hits and len(self.hits) >= MAX_BUCKETS:
                return False
            bucket = self.hits.setdefault(key, deque())
            while bucket and now - bucket[0] >= window:
                bucket.popleft()
            allowed = len(bucket) < limit
            if allowed:
                bucket.append(now)
            self.hits.move_to_end(key)
            self._evict(now, window=window)
            return allowed

    def _evict(self, now, *, window):
        while len(self.hits) >= MAX_BUCKETS:
            key, bucket = next(iter(self.hits.items()))
            if bucket and now - bucket[-1] < window:
                break
            self.hits.pop(key)


class RedisLimits:
    def __init__(self, connection):
        self.connection = connection

    async def allow(self, key: str, *, limit: int, window: int):
        client = self.connection.client()
        now = int(time.time() * MILLISECONDS)
        result = await client.eval(WINDOW_LUA, 1, "mall:limit:" + key,
                                   now, window * MILLISECONDS, limit, str(uuid4()))
        return bool(result)
