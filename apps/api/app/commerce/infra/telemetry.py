"""Optional process instrumentation; disabled deployments import no telemetry SDK."""


def instrument(application, settings):
    if not settings.otel_enabled:
        return
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    from app.core import database

    FastAPIInstrumentor.instrument_app(application, excluded_urls="health.*,metrics")
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=database.engine.sync_engine)
    if settings.cache_backend == "redis" or settings.lock_backend == "redis":
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
