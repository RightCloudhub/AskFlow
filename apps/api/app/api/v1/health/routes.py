"""Health and metrics endpoints (S-02 / S-03)."""

from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.core.config import get_settings
from app.core.database import engine
from app.middleware.metrics import DEPENDENCY_UP, metrics_payload
from app.schemas.common import HealthDependency, HealthResponse

router = APIRouter()


@router.get("/health", response_model=None)
async def health() -> HealthResponse | JSONResponse:
    settings = get_settings()
    deps: list[HealthDependency] = []

    # postgres / sqlite
    db_status = "down"
    db_detail = None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "up"
        DEPENDENCY_UP.labels(name="postgres").set(1)
    except Exception as exc:
        db_detail = str(exc)
        DEPENDENCY_UP.labels(name="postgres").set(0)
    deps.append(HealthDependency(name="database", status=db_status, detail=db_detail))

    # redis optional — unconfigured is not a hard failure for MVP local
    redis_status = "up" if not settings.redis_url else "down"
    redis_detail = "not_configured" if not settings.redis_url else None
    if settings.redis_url:
        try:
            import redis.asyncio as redis

            client = redis.from_url(settings.redis_url)
            await client.ping()
            await client.aclose()
            redis_status = "up"
            DEPENDENCY_UP.labels(name="redis").set(1)
        except Exception as exc:
            redis_status = "down"
            redis_detail = str(exc)
            DEPENDENCY_UP.labels(name="redis").set(0)
    else:
        DEPENDENCY_UP.labels(name="redis").set(0)
    deps.append(HealthDependency(name="redis", status=redis_status, detail=redis_detail))

    overall = "ok" if db_status == "up" else "down"
    body = HealthResponse(
        status=overall,
        version=__version__,
        env=settings.env,
        dependencies=deps,
        extras={"harness_policy": settings.harness_policy_version},
    )
    # PRD §12.1 #12: dependency abnormal → 503
    if db_status != "up":
        return JSONResponse(status_code=503, content=body.model_dump())
    return body


@router.get("/metrics")
async def metrics() -> Response:
    payload, content_type = metrics_payload()
    return Response(content=payload, media_type=content_type)
