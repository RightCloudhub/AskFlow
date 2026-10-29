"""Bounded read-only port checks; optional outages expose fallback state."""

import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import text

from app.commerce.infra.errors import dependency_errors
from app.commerce.infra.matrix import capability_matrix
from app.commerce.infra.runtime import infra
from app.core import database
from app.core.config import get_settings

REDIS_PORTS = frozenset({"cache", "lock", "rate_limit", "sessions", "flash_sale"})
CRITICAL_PORTS = frozenset({"database", "lock", "rate_limit", "flash_sale"})
DEFAULT_RABBIT_PORT = 5672
DEFAULT_KAFKA_PORT = 9092


async def check(action):
    try:
        return bool(await asyncio.wait_for(action(), get_settings().external_timeout_seconds))
    except dependency_errors():
        return False


async def database_up():
    async with database.engine.connect() as connection:
        await connection.execute(text("SELECT 1 FROM idempotency_records LIMIT 1"))
    return True


async def redis_up():
    return await infra().redis.client().ping()


async def search_up():
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.external_timeout_seconds) as client:
        response = await client.get(settings.search_url.rstrip("/") + "/_cluster/health")
        response.raise_for_status()
        return response.json().get("status") != "red"


async def objects_up():
    objects = infra().objects
    if get_settings().object_store == "local":
        root = Path(objects.root)
        while not root.exists() and root.parent != root:
            root = root.parent
        return root.is_dir() and os.access(root, os.R_OK | os.W_OK)
    await asyncio.to_thread(objects._client().head_bucket, Bucket=get_settings().s3_bucket)
    return True


async def tcp_up(url, default_port):
    parsed = urlparse(url if "://" in url else "tcp://" + url)
    _reader, writer = await asyncio.open_connection(parsed.hostname, parsed.port or default_port)
    writer.close()
    await writer.wait_closed()
    return True


async def broker_up():
    settings = get_settings()
    if settings.event_bus == "rabbitmq":
        return await tcp_up(settings.rabbitmq_url or "", DEFAULT_RABBIT_PORT)
    return await tcp_up((settings.kafka_bootstrap_servers or "").split(",")[0], DEFAULT_KAFKA_PORT)


async def port_matrix():
    settings = get_settings()
    matrix = capability_matrix(settings)
    db_ok = await check(database_up)
    redis_needed = any(p["implementation"] in {"redis", "redis_streams"} for p in matrix["ports"])
    redis_ok = await check(redis_up) if redis_needed else True
    external = {}
    if settings.search_backend == "elasticsearch":
        external["search"] = await check(search_up)
    external["object_store"] = await check(objects_up)
    if settings.event_bus in {"rabbitmq", "kafka"}:
        external["event_bus"] = await check(broker_up)
    for port in matrix["ports"]:
        port["state"] = port_state(port, database_ok=db_ok, redis_ok=redis_ok, external=external)
        port["critical"] = port["port"] in CRITICAL_PORTS
    ready = all(p["state"] == "up" for p in matrix["ports"] if p["critical"])
    return {"status": "ok" if ready else "down", **matrix}


def port_state(port, *, database_ok, redis_ok, external):
    name, backend = port["port"], port["implementation"]
    if backend in {"redis", "redis_streams"}:
        available = redis_ok
    elif name in external:
        available = external[name]
    elif name in {"email", "sms"} and backend != "console":
        return "unverified"
    else:
        available = database_ok
    return "up" if available else "down"
