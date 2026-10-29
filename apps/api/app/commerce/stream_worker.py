"""Redis flash streams wake durable database jobs; ACK follows a committed outcome."""

from datetime import UTC, datetime
from uuid import uuid4

from app.commerce.infra.runtime import infra
from app.commerce.inventory.models import FlashRequest
from app.commerce.job_registry import JOBS
from app.core import database
from app.core.config import get_settings

STREAM = "mall:flash:requests"
GROUP = "mall-order-workers"
CONSUMER = str(uuid4())
MILLISECONDS = 1000


async def poll():
    settings = get_settings()
    if settings.flash_sale_backend != "redis":
        return
    client = infra().redis.client()
    await group(client)
    reclaimed = await client.xautoclaim(STREAM, GROUP, CONSUMER,
        min_idle_time=settings.mall_worker_lease_seconds * MILLISECONDS,
        start_id="0-0", count=settings.mall_worker_batch)
    batches = await client.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=settings.mall_worker_batch)
    messages = list(reclaimed[1])
    for _stream, entries in batches:
        messages.extend(entries)
    for message_id, fields in messages:
        if await process(fields.get("request_id", ""), message_id=message_id):
            await client.xack(STREAM, GROUP, message_id)


async def group(client):
    from redis.exceptions import ResponseError

    try:
        await client.xgroup_create(STREAM, GROUP, id="0-0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def process(request_id: str, *, message_id: str):
    from app.commerce.worker import run_item

    async with database.SessionLocal() as db:
        row = await db.get(FlashRequest, request_id)
        if row is None:
            published = datetime.fromtimestamp(int(message_id.split("-")[0]) / MILLISECONDS, UTC)
            return (datetime.now(UTC) - published).total_seconds() > get_settings().mall_reservation_seconds
        if row.status != "queued":
            return True
    job = next(item for item in JOBS if item.name == "flash")
    return bool(await run_item(job, request_id))
