from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, require_admin
from app.models.user import User
from app.services.tools.registry import register_mcp_tools_from_settings, registry

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/sync")
async def sync_mcp_tools(db: DbSession, _user: User = Depends(require_admin)) -> dict:
    registered = await register_mcp_tools_from_settings(db)
    return {
        "registered": registered,
        "all_tools": registry.names(),
        "mcp_tools": [n for n in registry.names() if registry.is_mcp(n)],
    }


@router.get("/tools")
async def list_tools(_user: User = Depends(require_admin)) -> dict:
    return {
        "tools": registry.names(),
        "mcp": [n for n in registry.names() if registry.is_mcp(n)],
    }
