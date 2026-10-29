"""Secret-free infrastructure matrix derived from the selected implementations."""


def capability_matrix(settings) -> dict:
    choices = {
        "database": "sqlite" if settings.database_url.startswith("sqlite") else "postgresql",
        "cache": settings.cache_backend, "lock": settings.lock_backend,
        "rate_limit": settings.rate_limit_backend, "event_bus": settings.event_bus,
        "search": settings.search_backend, "object_store": settings.object_store,
        "sessions": settings.session_backend, "email": settings.notify_email,
        "sms": settings.notify_sms, "workers": settings.worker_mode,
        "flash_sale": settings.flash_sale_backend,
    }
    degraded = {"sqlite", "memory", "local", "console", "inprocess", "like", "off"}
    notes = {
        "sqlite": "Single writer; no replica or automatic failover",
        "memory": "Per-process coordination/cache only",
        "local": "Local disk; no shared object store or CDN",
        "console": "Metadata-only mock sender; inbox notifications remain available",
        "inprocess": "Worker shares API lifecycle; database leases still required",
        "like": "Database substring search; limited relevance ranking",
        "off": "Cache disabled; database is authoritative",
        "database": "Database conditional updates and durable outbox polling",
        "outbox": "Database polling; higher latency than streaming brokers",
    }
    descriptions = {"sessions": "Database authoritative sessions; selected backend caches revocation tombstones only",
                    "event_bus": "Internal consumers use transactional outbox; selected broker publishes integration events",
                    "flash_sale": "Database conditional allocation; Redis adds burst admission and stream notifications"}
    return {"preset": settings.askflow_infra, "instance_count": settings.instance_count,
            "ports": [{"port": port, "implementation": backend,
                       "multi_instance_safe": backend not in {"memory", "sqlite", "local"},
                       "degraded": backend in degraded,
                       "description": descriptions.get(port, notes.get(backend, "Shared adapter"))}
                      for port, backend in choices.items()]}
