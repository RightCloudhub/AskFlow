"""AskFlow API entrypoint (PRD §3 / S-01 fail-safe)."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import build_api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.metrics import PROCESS_INFO
from app.middleware.rate_limit import RateLimitMiddleware
from app.plugins.loader import boot_plugins, load_plugins, shutdown_plugins
from app.plugins.runtime import get_app_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("askflow")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.assert_startup_safe()
    ctx = get_app_context()
    if ctx is None:
        ctx = load_plugins(settings)
    PROCESS_INFO.info(
        {
            "version": settings.app_version,
            "harness_policy": settings.harness_policy_version,
            "env": settings.env,
            "profile": settings.askflow_profile,
            "plugins": ",".join(ctx.loaded_plugins),
        }
    )
    await init_db()
    await boot_plugins(ctx)
    logger.info(
        "AskFlow API started env=%s version=%s profile=%s plugins=%s",
        settings.env,
        __version__,
        settings.askflow_profile,
        ctx.loaded_plugins,
    )
    job_task: asyncio.Task | None = None
    if settings.env != "test" and settings.sweeper_enabled:
        from app.workers.enterprise_jobs import periodic_loop

        job_task = asyncio.create_task(periodic_loop(settings), name="enterprise_jobs")
    try:
        yield
    finally:
        if job_task is not None:
            job_task.cancel()
            try:
                await job_task
            except asyncio.CancelledError:
                pass
        await shutdown_plugins(get_app_context())
        logger.info("AskFlow API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    # Clear cached settings if tests mutated env before import
    ctx = load_plugins(settings)
    # Hide OpenAPI in staging/production (M3)
    docs = None if settings.is_production_like else "/docs"
    redoc = None if settings.is_production_like else "/redoc"
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url=docs,
        redoc_url=redoc,
    )
    # Starlette: last added = outermost. Rate limit outermost after CORS.
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = build_api_router(ctx)
    application.include_router(api, prefix=settings.api_prefix)

    # Root-level health/metrics as per PRD §7.1
    from app.api.v1.health.routes import health, metrics

    application.add_api_route(
        "/health", health, methods=["GET"], tags=["health"], response_model=None
    )
    application.add_api_route("/metrics", metrics, methods=["GET"], tags=["health"])

    @application.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
            "profile": settings.askflow_profile,
        }

    return application


app = create_app()
