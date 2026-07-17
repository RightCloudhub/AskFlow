"""Periodic enterprise jobs: handoff timeout sweep + SLA scan (business loop).

Runs inside API lifespan when not in test env. Multi-worker safe via CAS
in HandoffTimeoutSweeper / ticket updates; SLA scan is idempotent per state.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core import database as dbmod
from app.core.config import Settings, get_settings
from app.middleware.metrics import SLA_EVENTS_TOTAL
from app.models.enums import NotifyEvent
from app.services.handoff.timeout import HandoffTimeoutSweeper
from app.services.notify.service import NotifyService
from app.services.ticket.sla.engine import SLAEngine

logger = logging.getLogger("askflow.jobs")

DEFAULT_INTERVAL_SEC = 60
MIN_INTERVAL_SEC = 15


async def run_once() -> dict[str, Any]:
    """Execute one sweep cycle (also usable from admin / tests)."""
    async with dbmod.SessionLocal() as db:
        handoff_out = await HandoffTimeoutSweeper(db).sweep()
        changes = await SLAEngine(db).scan()
        notify = NotifyService(db)
        for ch in changes:
            event = (
                NotifyEvent.SLA_BREACHED.value
                if ch.current == "breached"
                else NotifyEvent.SLA_WARNING.value
            )
            SLA_EVENTS_TOTAL.labels(state=ch.current, reason=ch.reason or "unknown").inc()
            await notify.emit_safe(
                event,
                {
                    "ticket_id": ch.ticket_id,
                    "previous": ch.previous,
                    "current": ch.current,
                    "reason": ch.reason,
                },
            )
        await db.commit()
        return {
            "handoff_swept": len(handoff_out),
            "sla_changes": len(changes),
        }


async def periodic_loop(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    interval = max(MIN_INTERVAL_SEC, int(getattr(settings, "sweeper_interval_seconds", DEFAULT_INTERVAL_SEC)))
    logger.info("enterprise jobs loop started interval_sec=%s", interval)
    while True:
        try:
            result = await run_once()
            logger.info(
                "enterprise jobs ok handoff=%s sla=%s",
                result.get("handoff_swept"),
                result.get("sla_changes"),
            )
        except asyncio.CancelledError:
            logger.info("enterprise jobs loop cancelled")
            raise
        except Exception:
            logger.exception("enterprise jobs cycle failed")
        await asyncio.sleep(interval)
