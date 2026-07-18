"""Health and metrics endpoints (S-02 / S-03)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.core.config import Settings, get_settings
from app.core.database import engine
from app.middleware.metrics import DEPENDENCY_UP, metrics_payload
from app.schemas.common import HealthDependency, HealthResponse

router = APIRouter()

HTTP_SERVICE_UNAVAILABLE = 503
HTTP_UNAUTHORIZED = 401


@router.get("/health", response_model=None)
async def health() -> HealthResponse | JSONResponse:
    settings = get_settings()
    deps = [
        await _check_database(settings),
        await _check_redis(settings),
        _check_vector(settings),
    ]
    db_up = next(d.status == "up" for d in deps if d.name == "database")
    overall = "ok" if db_up else "down"
    body = HealthResponse(
        status=overall,
        version=__version__,
        env=settings.env,
        dependencies=deps,
        extras={"harness_policy": settings.harness_policy_version},
    )
    # PRD §12.1 #12: dependency abnormal → 503
    if not db_up:
        return JSONResponse(status_code=HTTP_SERVICE_UNAVAILABLE, content=body.model_dump())
    return body


async def _check_database(settings: Settings) -> HealthDependency:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        DEPENDENCY_UP.labels(name="postgres").set(1)
        return HealthDependency(name="database", status="up", detail=None)
    except Exception:
        DEPENDENCY_UP.labels(name="postgres").set(0)
        detail = "unavailable" if settings.is_production_like else "error"
        return HealthDependency(name="database", status="down", detail=detail)


async def _check_redis(settings: Settings) -> HealthDependency:
    if not settings.redis_url:
        DEPENDENCY_UP.labels(name="redis").set(0)
        return HealthDependency(name="redis", status="up", detail="not_configured")
    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        DEPENDENCY_UP.labels(name="redis").set(1)
        return HealthDependency(name="redis", status="up", detail=None)
    except Exception:
        DEPENDENCY_UP.labels(name="redis").set(0)
        detail = "unavailable" if settings.is_production_like else "error"
        return HealthDependency(name="redis", status="down", detail=detail)


def _check_vector(settings: Settings) -> HealthDependency:
    """Memory always up; configured Chroma must be reachable."""
    try:
        from app.services.rag.vector.store import get_default_vector_store

        store = get_default_vector_store(settings)
        status, detail = _vector_status(settings, store)
        DEPENDENCY_UP.labels(name="vector").set(1 if status == "up" else 0)
        return HealthDependency(name="vector", status=status, detail=detail)
    except Exception:
        DEPENDENCY_UP.labels(name="vector").set(0)
        detail = "unavailable" if settings.is_production_like else "error"
        return HealthDependency(name="vector", status="down", detail=detail)


def _vector_status(settings: Settings, store: object) -> tuple[str, str]:
    backend = getattr(store, "backend_name", "memory")
    chroma_configured = bool(settings.chroma_host or settings.chroma_persist_dir)
    if not chroma_configured:
        return "up", str(backend)
    chroma = getattr(store, "chroma", None)
    if chroma is not None and getattr(chroma, "available", False):
        return "up", str(backend)
    return "down", "chroma_unavailable"


def _metrics_authorized(request: Request | None) -> bool:
    settings = get_settings()
    token = settings.metrics_token
    if not token:
        return True
    if not settings.is_production_like:
        return True
    if request is None:
        return False
    return request.headers.get("x-metrics-token") == token


@router.get("/metrics")
async def metrics(request: Request) -> Response:
    """Prometheus scrape. Optional METRICS_TOKEN in staging/production."""
    if not _metrics_authorized(request):
        raise HTTPException(status_code=HTTP_UNAUTHORIZED, detail="metrics_token_required")
    payload, content_type = metrics_payload()
    return Response(content=payload, media_type=content_type)
