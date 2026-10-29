"""Bounded external calls; write failures must be reconciled, never blindly retried."""

import asyncio
import random
import time
from http import HTTPStatus

import httpx

from app.commerce.core.errors import MallError
from app.commerce.infra.metrics import BREAKER_STATE

HTTP_SERVER_ERROR = 500


class CircuitBreaker:
    def __init__(self, name: str, settings):
        self.name, self.settings = name, settings
        self.failures, self.opened_at, self.probe = 0, None, asyncio.Lock()

    async def call(self, action, *, readonly: bool = True):
        self._check_open()
        if self.opened_at is not None:
            if self.probe.locked():
                raise MallError("dependency_unavailable", status=HTTPStatus.SERVICE_UNAVAILABLE)
            async with self.probe:
                return await self._attempts(action, readonly=readonly)
        return await self._attempts(action, readonly=readonly)

    def _check_open(self):
        if self.opened_at is None:
            return
        if time.monotonic() - self.opened_at < self.settings.breaker_reset_seconds:
            raise MallError("dependency_unavailable", status=HTTPStatus.SERVICE_UNAVAILABLE)

    async def _attempts(self, action, *, readonly):
        retries = self.settings.external_max_retries if readonly else 0
        for attempt in range(retries + 1):
            try:
                result = await asyncio.wait_for(action(), self.settings.external_timeout_seconds)
            except (TimeoutError, ConnectionError, OSError, httpx.TransportError, httpx.HTTPStatusError) as exc:
                await self._retry(exc, attempt=attempt, retries=retries)
                continue
            self.failures, self.opened_at = 0, None
            BREAKER_STATE.labels(adapter=self.name).set(0)
            return result

    async def _retry(self, exc, *, attempt, retries):
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < HTTP_SERVER_ERROR:
            raise exc
        self._failed()
        if attempt == retries:
            raise MallError("dependency_unavailable", status=HTTPStatus.SERVICE_UNAVAILABLE) from None
        delay = self.settings.external_retry_base_seconds * (2 ** attempt)
        await asyncio.sleep(delay + random.random() * delay)

    def _failed(self):
        self.failures += 1
        if self.failures >= self.settings.breaker_failures:
            self.opened_at = time.monotonic()
            BREAKER_STATE.labels(adapter=self.name).set(1)
