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
from app.core.background import start_background_tasks
from app.core.schema import prepare_schema
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
    await prepare_schema(settings)
    await boot_plugins(ctx)
    logger.info(
        "AskFlow API started env=%s version=%s profile=%s plugins=%s",
        settings.env,
        __version__,
        settings.askflow_profile,
        ctx.loaded_plugins,
    )
    bg_tasks = _start_background_tasks(settings)
    try:
        yield
    finally:
        await _stop_background_tasks(bg_tasks)
        await shutdown_plugins(get_app_context())
        logger.info("AskFlow API shutting down")


def _start_background_tasks(settings) -> list[asyncio.Task]:
    return start_background_tasks(settings)


async def _stop_background_tasks(tasks: list[asyncio.Task]) -> None:
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


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
    _configure_middleware(application, ctx)
    _configure_routes(application, ctx)
    if ctx.enabled("mall_core"):
        from app.commerce.infra.telemetry import instrument

        instrument(application, settings)
    return application


def _configure_middleware(application, ctx):
    settings = ctx.settings
    if not ctx.enabled("mall_core"):
        application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RateLimitMiddleware)
    if ctx.enabled("mall_core"):
        from app.commerce.core.error_handlers import install_error_handlers
        from app.commerce.infra.middleware import MallLimitMiddleware
        from app.commerce.infra.logging import MallRequestLogging

        application.add_middleware(MallLimitMiddleware)
        application.add_middleware(MallRequestLogging)
        install_error_handlers(application)
        application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def _configure_routes(application, ctx):
    from app.api.v1.health.routes import health, metrics

    application.include_router(build_api_router(ctx), prefix=ctx.settings.api_prefix)
    application.include_router(ctx.root_router)
    if ctx.enabled("mall_core"):
        from app.commerce.infra.web import mount

        mount(application)
    application.add_api_route("/health", health, methods=["GET"], tags=["health"], response_model=None)
    application.add_api_route("/metrics", metrics, methods=["GET"], tags=["health"])

    @application.get("/")
    async def root():
        return {"name": ctx.settings.app_name, "version": __version__, "docs": "/docs",
                "health": "/health", "profile": ctx.settings.askflow_profile}


app = create_app()
