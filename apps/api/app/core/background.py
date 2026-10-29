"""Background loop selection preserves legacy profiles and separate mall workers."""

import asyncio
from importlib import import_module

from app.plugins.runtime import get_app_context


def start_background_tasks(settings):
    if settings.env == "test":
        return []
    ctx = get_app_context()
    mall_enabled = ctx is not None and ctx.enabled("mall_core")
    if mall_enabled and settings.worker_mode == "separate":
        return []
    loops = _legacy_loops(settings, ctx)
    if mall_enabled and settings.mall_worker_enabled:
        loops.append(("mall", "app.commerce.worker", "periodic_loop", ()))
    return [asyncio.create_task(getattr(import_module(module), function)(*args), name=name)
            for name, module, function, args in loops]


def _legacy_loops(settings, ctx):
    from app.services.agent.service.settings import ServiceSettings
    from app.services.channels.settings import ChannelSettings
    from app.services.outbox.settings import OutboxSettings

    candidates = [
        (ServiceSettings().enabled and ctx is not None and ctx.enabled("agent"),
         "service_tasks", "app.workers.service_tasks", "periodic_loop", ()),
        (settings.sweeper_enabled, "enterprise_jobs", "app.workers.enterprise_jobs", "periodic_loop", (settings,)),
        (settings.index_worker_enabled, "index_worker", "app.workers.index_worker.consumer", "consumer_loop", (settings,)),
        (OutboxSettings().enabled, "outbox_relay", "app.workers.outbox_relay", "periodic_loop", ()),
        (ChannelSettings().inbox_relay_enabled, "channel_inbox_relay", "app.workers.channel_inbox_relay", "periodic_loop", ()),
    ]
    return [(name, module, function, args) for enabled, name, module, function, args in candidates if enabled]
