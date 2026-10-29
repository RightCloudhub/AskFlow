"""AppContext-owned adapters avoid cached state leaking between test profiles."""

from app.commerce.infra.bus import KafkaBus, OutboxBus, RabbitBus, RedisStreamsBus
from app.commerce.infra.cache import CachedReads, MemoryCache, OffCache, RedisCache
from app.commerce.infra.limits import MemoryLimits, RedisLimits
from app.commerce.infra.locks import MemoryLocks, PostgresLocks, RedisLocks
from app.commerce.infra.objects import LocalObjects, S3Objects
from app.commerce.infra.redis_client import RedisConnection
from app.commerce.infra.resilience import CircuitBreaker
from app.commerce.infra.search import DatabaseSearch, ElasticSearch
from app.commerce.infra.senders import ConsoleSender, HttpSmsSender, SmtpSender
from app.plugins.runtime import require_app_context


class Infra:
    def __init__(self, settings):
        self.settings = settings
        self.redis = RedisConnection(settings.redis_url, timeout=settings.external_timeout_seconds)
        self.cache = self._cache()
        self.locks = self._locks()
        self.limits = RedisLimits(self.redis) if settings.rate_limit_backend == "redis" else MemoryLimits()
        self.objects = S3Objects(settings) if settings.object_store == "s3" else LocalObjects(settings)
        self.bus = self._bus()
        self.search = self._search()
        self.email = SmtpSender(settings) if settings.notify_email == "smtp" else ConsoleSender()
        self.sms = HttpSmsSender(settings) if settings.notify_sms != "console" else ConsoleSender()
        self.mailbox = {}

    def _cache(self):
        factories = {"off": lambda: OffCache(), "memory": lambda: MemoryCache(self.settings.cache_max_entries),
                     "redis": lambda: RedisCache(self.redis)}
        return CachedReads(factories[self.settings.cache_backend](), self.settings)

    def _locks(self):
        factories = {"memory": lambda: MemoryLocks(self.settings.lock_shards),
                     "pg": lambda: PostgresLocks(), "redis": lambda: RedisLocks(self.redis, self.settings)}
        return factories[self.settings.lock_backend]()

    def _bus(self):
        factories = {"outbox": lambda: OutboxBus(), "redis_streams": lambda: RedisStreamsBus(self.redis),
                     "rabbitmq": lambda: RabbitBus(self.settings), "kafka": lambda: KafkaBus(self.settings)}
        return factories[self.settings.event_bus]()

    def _search(self):
        if self.settings.search_backend == "elasticsearch":
            return ElasticSearch(self.settings, CircuitBreaker("search", self.settings))
        return DatabaseSearch(self.settings.search_backend)

    async def close(self):
        await self.bus.close()
        await self.redis.close()
        self.mailbox.clear()


def infra() -> Infra:
    return require_app_context().services["mall_infra"]
