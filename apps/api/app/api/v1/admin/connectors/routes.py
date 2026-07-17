from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.user import User
from app.services.connectors.service import ConnectorService

router = APIRouter(dependencies=[Depends(require_admin)])


class ConnectorIn(BaseModel):
    name: str
    base_url: str
    method: str = "GET"
    path_template: str = "/"
    auth_header: str | None = None
    timeout_ms: int = 5000
    enabled: bool = True
    description: str = ""
    headers: dict[str, Any] = Field(default_factory=dict)


class InvokeIn(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def list_connectors(db: DbSession, _user: User = Depends(require_admin)) -> list[dict]:
    svc = ConnectorService(db)
    await svc.ensure_defaults()
    rows = await svc.list_connectors()
    return [
        {
            "id": r.id,
            "name": r.name,
            "base_url": r.base_url,
            "method": r.method,
            "path_template": r.path_template,
            "enabled": r.enabled,
            "description": r.description,
        }
        for r in rows
    ]


@router.put("/{name}")
async def upsert_connector(
    name: str,
    body: ConnectorIn,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    row = await ConnectorService(db).upsert(
        name=name,
        base_url=body.base_url,
        method=body.method,
        path_template=body.path_template,
        auth_header=body.auth_header,
        timeout_ms=body.timeout_ms,
        enabled=body.enabled,
        description=body.description,
        headers=body.headers,
        actor_id=user.id,
    )
    return {"id": row.id, "name": row.name, "enabled": row.enabled}


@router.post("/{name}/invoke")
async def invoke_connector(
    name: str,
    body: InvokeIn,
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    return await ConnectorService(db).invoke(name, params=body.params)
