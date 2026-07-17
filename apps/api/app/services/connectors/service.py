"""Configuration-driven HTTP connectors (PRD E6 / §12.2) — ≥2 business connectors."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.metrics import CONNECTOR_TOTAL
from app.models.connector import ConnectorConfig
from app.services.audit.logger.service import AuditService


class ConnectorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_defaults(self) -> None:
        defaults = [
            {
                "name": "order_status",
                "base_url": "https://httpbin.org",
                "method": "GET",
                "path_template": "/get",
                "description": "Order status HTTP connector (config-driven)",
            },
            {
                "name": "crm_lookup",
                "base_url": "https://httpbin.org",
                "method": "GET",
                "path_template": "/get",
                "description": "CRM account lookup connector",
            },
        ]
        for d in defaults:
            existing = await self.db.execute(
                select(ConnectorConfig).where(ConnectorConfig.name == d["name"])
            )
            if existing.scalar_one_or_none() is None:
                self.db.add(ConnectorConfig(**d))
        await self.db.flush()

    async def list_connectors(self) -> list[ConnectorConfig]:
        result = await self.db.execute(select(ConnectorConfig).order_by(ConnectorConfig.name))
        return list(result.scalars().all())

    async def upsert(
        self,
        *,
        name: str,
        base_url: str,
        method: str = "GET",
        path_template: str = "/",
        auth_header: str | None = None,
        timeout_ms: int = 5000,
        enabled: bool = True,
        description: str = "",
        headers: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> ConnectorConfig:
        result = await self.db.execute(select(ConnectorConfig).where(ConnectorConfig.name == name))
        row = result.scalar_one_or_none()
        if row is None:
            row = ConnectorConfig(name=name, base_url=base_url)
            self.db.add(row)
        row.base_url = base_url
        row.method = method.upper()
        row.path_template = path_template
        row.auth_header = auth_header
        row.timeout_ms = timeout_ms
        row.enabled = enabled
        row.description = description
        row.headers = headers or {}
        await self.db.flush()
        await self.db.refresh(row)
        await AuditService(self.db).log(
            action="connector.upsert",
            resource_type="connector",
            resource_id=row.id,
            actor_id=actor_id,
            detail={"name": name, "base_url": base_url},
        )
        return row

    async def invoke(
        self,
        name: str,
        *,
        params: dict[str, Any] | None = None,
        mock_transport: httpx.AsyncBaseTransport | None = None,
    ) -> dict[str, Any]:
        result = await self.db.execute(select(ConnectorConfig).where(ConnectorConfig.name == name))
        cfg = result.scalar_one_or_none()
        if cfg is None:
            CONNECTOR_TOTAL.labels(name=name, status="missing").inc()
            return {"status": "error", "error_class": "not_found", "message": f"connector {name}"}
        if not cfg.enabled:
            CONNECTOR_TOTAL.labels(name=name, status="disabled").inc()
            return {"status": "error", "error_class": "disabled", "message": "connector disabled"}

        path = cfg.path_template
        if params:
            for k, v in params.items():
                path = path.replace("{" + k + "}", str(v))
        url = urljoin(cfg.base_url.rstrip("/") + "/", path.lstrip("/"))
        headers = dict(cfg.headers or {})
        if cfg.auth_header:
            headers["Authorization"] = cfg.auth_header

        timeout = max(cfg.timeout_ms, 100) / 1000.0
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=mock_transport) as client:
                resp = await client.request(cfg.method, url, params=params or {}, headers=headers)
            if resp.status_code >= 400:
                # Upstream failure → deterministic mock (enterprise offline degradation)
                CONNECTOR_TOTAL.labels(name=name, status="http_mock").inc()
                return {
                    "status": "mock",
                    "error_class": "http_4xx" if resp.status_code < 500 else "http_5xx",
                    "message": f"HTTP {resp.status_code}",
                    "connector": name,
                    "data_source": "mock",
                    "data": {
                        "mock": True,
                        "reason": f"upstream_http_{resp.status_code}",
                        "params": params or {},
                    },
                }
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text[:2000]}
            CONNECTOR_TOTAL.labels(name=name, status="ok").inc()
            return {"status": "ok", "connector": name, "data": data, "data_source": "connector"}
        except httpx.TimeoutException:
            CONNECTOR_TOTAL.labels(name=name, status="timeout_mock").inc()
            return {
                "status": "mock",
                "error_class": "timeout",
                "connector": name,
                "data_source": "mock",
                "data": {"mock": True, "reason": "timeout", "params": params or {}},
            }
        except Exception as exc:
            # Offline / network failure: deterministic mock so main ops paths stay usable
            CONNECTOR_TOTAL.labels(name=name, status="error_mock").inc()
            return {
                "status": "mock",
                "error_class": "error",
                "message": str(exc),
                "connector": name,
                "data_source": "mock",
                "data": {"mock": True, "reason": str(exc)[:200], "params": params or {}},
            }
