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
from app.services.handoff.timeout import HandoffTimeoutSweeper
from app.services.notify.service import NotifyService
from app.services.ticket.sla.engine import SLAEngine
from app.services.ticket.sla.publish import publish_sla_changes

logger = logging.getLogger("askflow.jobs")

DEFAULT_INTERVAL_SEC = 60
MIN_INTERVAL_SEC = 15


async def run_once() -> dict[str, Any]:
    """Execute one sweep cycle (also usable from admin / tests).

    State changes are committed first; webhooks and metrics fire only for committed rows,
    so a rolled-back cycle never notifies and the next cycle cannot double-notify (D-09).
    """
    async with dbmod.SessionLocal() as db:
        sweeper = HandoffTimeoutSweeper(db)
        handoff_out = await sweeper.sweep()
        changes = await SLAEngine(db).scan()
        await db.commit()
        await sweeper.publish(handoff_out)
        await publish_sla_changes(NotifyService(db), changes)
        await db.commit()
        return {"handoff_swept": len(handoff_out), "sla_changes": len(changes)}


async def periodic_loop(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    interval = max(
        MIN_INTERVAL_SEC, int(getattr(settings, "sweeper_interval_seconds", DEFAULT_INTERVAL_SEC))
    )
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
