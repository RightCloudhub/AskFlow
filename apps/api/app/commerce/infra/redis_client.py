"""Shared optional Redis connection, with no import/connect at module load."""

DEFAULT_TIMEOUT_SECONDS = 5.0


class RedisConnection:
    def __init__(self, url: str | None, *, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.url, self._client, self.timeout = url, None, timeout

    def client(self):
        if not self.url:
            raise RuntimeError("REDIS_URL is required by the selected adapter")
        if self._client is None:
            from redis.asyncio import from_url

            self._client = from_url(self.url, decode_responses=True,
                socket_connect_timeout=self.timeout, socket_timeout=self.timeout,
                retry_on_timeout=False)
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None
