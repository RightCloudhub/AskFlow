"""Versioned configuration, role grants and operational summary."""

from http import HTTPStatus

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select

from app.commerce.admin.models import AdminRole, SettingRevision, UserRoleGrant
from app.commerce.admin.permissions import require, seed_roles
from app.commerce.admin.roles_api import router as roles_router
from app.commerce.admin.settings_service import change, list_settings
from app.commerce.core.commands import command
from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.repository import insert_once
from app.commerce.core.schemas import Schema, Versioned

RBAC_WRITE = require("rbac:write")
SETTINGS_WRITE = require("settings:write")

router = APIRouter()
router.include_router(roles_router)


class SettingInput(Versioned):
    value: int = Field(strict=True, ge=0)


class Grant(Schema):
    user_id: str
    role: str


class Rollback(Versioned):
    source_version: int = Field(ge=0)


@router.get("/settings")
async def settings(ctx=SETTINGS_WRITE):
    return {"items": await list_settings(ctx.db)}


@router.put("/settings/{key}")
async def setting(key: str, payload: SettingInput, ctx=SETTINGS_WRITE):
    return await command(ctx, "settings.change:" + key, payload=payload,
                         action=lambda: change(ctx, key, payload))


@router.get("/roles")
async def roles(ctx=RBAC_WRITE):
    rows = await ctx.db.scalars(select(AdminRole).order_by(AdminRole.code))
    return {"items": [{"id": row.id, "code": row.code, "name": row.name,
                       "builtin": row.builtin, "version": row.version} for row in rows]}


@router.post("/roles/grant")
async def grant(payload: Grant, ctx=RBAC_WRITE):
    async def perform():
        from app.commerce.account.identity import active_identity

        if await active_identity(ctx.db, payload.user_id) is None:
            raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
        await seed_roles(ctx.db)
        role = await ctx.db.scalar(select(AdminRole).where(AdminRole.code == payload.role))
        if role is None:
            raise MallError("role_not_found", status=HTTPStatus.NOT_FOUND)
        await insert_once(ctx.db, UserRoleGrant, values={"user_id": payload.user_id,
            "role_id": role.id, "assigned_by": ctx.user.id}, unique=["user_id", "role_id"])
        return {"status": "granted", "role": payload.role, "user_id": payload.user_id}

    return await command(ctx, "rbac.grant", payload=payload, action=perform)


@router.get("/settings/{key}/history")
async def history(key: str, before: int | None = None, ctx=SETTINGS_WRITE):
    query = select(SettingRevision).where(SettingRevision.key == key)
    if before is not None:
        query = query.where(SettingRevision.version < before)
    rows = await ctx.db.scalars(query.order_by(SettingRevision.version.desc()).limit(PAGE_SIZE))
    return {"items": [{"version": row.version, "value": row.value,
                        "modified_by": row.modified_by} for row in rows]}


@router.post("/settings/{key}/rollback")
async def rollback(key: str, payload: Rollback, ctx=SETTINGS_WRITE):
    async def perform():
        revision = await ctx.db.scalar(select(SettingRevision).where(
            SettingRevision.key == key, SettingRevision.version == payload.source_version))
        if revision is None:
            raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
        return await change(ctx, key, SettingInput(value=revision.value["value"],
                                                   expected_version=payload.expected_version))

    return await command(ctx, "settings.rollback:" + key, payload=payload, action=perform)
