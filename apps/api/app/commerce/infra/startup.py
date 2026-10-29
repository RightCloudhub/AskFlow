"""Fail-fast adapter requirements, without contacting external services."""

from importlib.util import find_spec


def assert_adapter_configuration(settings):
    redis_choices = {settings.cache_backend, settings.lock_backend, settings.rate_limit_backend,
                     settings.session_backend, settings.flash_sale_backend}
    needs_redis = "redis" in redis_choices or settings.event_bus == "redis_streams"
    requirements = [
        (needs_redis, settings.redis_url, "REDIS_URL"),
        (settings.search_backend == "elasticsearch", settings.search_url, "SEARCH_URL"),
        (settings.event_bus == "rabbitmq", settings.rabbitmq_url, "RABBITMQ_URL"),
        (settings.event_bus == "kafka", settings.kafka_bootstrap_servers, "KAFKA_BOOTSTRAP_SERVERS"),
        (settings.notify_email == "smtp", settings.smtp_host, "SMTP_HOST"),
        (settings.notify_sms != "console", settings.sms_provider_url, "SMS_PROVIDER_URL"),
        (settings.notify_sms != "console", settings.sms_provider_token, "SMS_PROVIDER_TOKEN"),
        (settings.object_store == "s3", settings.s3_bucket, "S3_BUCKET"),
    ]
    missing = [name for required, value, name in requirements if required and not value]
    if settings.lock_backend == "pg" and settings.database_url.startswith("sqlite"):
        missing.append("PostgreSQL DATABASE_URL for LOCK_BACKEND=pg")
    if missing:
        raise RuntimeError("Commerce adapter configuration missing: " + ", ".join(missing))
    assert_optional_clients(settings, needs_redis=needs_redis)


def assert_optional_clients(settings, *, needs_redis: bool):
    required = {"redis": needs_redis, "boto3": settings.object_store == "s3",
                "aio_pika": settings.event_bus == "rabbitmq",
                "aiokafka": settings.event_bus == "kafka"}
    missing = [name for name, selected in required.items() if selected and find_spec(name) is None]
    if missing:
        raise RuntimeError("Selected commerce adapters need optional clients: " + ", ".join(missing))
