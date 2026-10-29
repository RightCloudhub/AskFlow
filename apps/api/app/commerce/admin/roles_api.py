"""Custom roles and revocation use the same backend permission and audit boundary."""

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import delete, select

from app.commerce.admin.models import AdminRole, RolePermission, UserRoleGrant
from app.commerce.admin.permissions import PERMISSIONS, require
from app.commerce.core.commands import command
from app.commerce.core.constants import NAME_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas
from app.commerce.core.schemas import Schema, Versioned

router = APIRouter()


class RoleInput(Schema):
    code: str = Field(min_length=1, max_length=NAME_SIZE, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=NAME_SIZE)


class PermissionInput(Versioned):
    permissions: list[str] = Field(max_length=len(PERMISSIONS))


@router.post("/roles")
async def create(payload: RoleInput, ctx=require("rbac:write")):
    async def perform():
        row = AdminRole(code=payload.code, name=payload.name)
        ctx.db.add(row)
        await ctx.db.flush()
        return {"id": row.id, "code": row.code, "version": row.version}

    return await command(ctx, "role.create", payload=payload, action=perform)


@router.put("/roles/{role_id}/permissions")
async def permissions(role_id: str, payload: PermissionInput, ctx=require("rbac:write")):
    if not set(payload.permissions) <= PERMISSIONS:
        raise MallError("invalid_permission", status=422)

    async def perform():
        row = await ctx.db.scalar(select(AdminRole).where(AdminRole.id == role_id).with_for_update())
        if row is None:
            raise MallError("resource_not_found", status=404)
        if row.builtin:
            raise MallError("builtin_role_immutable")
        if row.version != payload.expected_version:
            raise MallError("version_conflict")
        previous = list(await ctx.db.scalars(select(RolePermission.permission_code).where(RolePermission.role_id == role_id)))
        await ctx.db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        ctx.db.add_all([RolePermission(role_id=role_id, permission_code=value) for value in sorted(set(payload.permissions))])
        await cas(ctx.db, row, values={})
        return {"id": role_id, "before": previous, "permissions": sorted(payload.permissions), "version": row.version}

    return await command(ctx, "role.permissions:" + role_id, payload=payload, action=perform)


@router.delete("/roles/grants/{user_id}/{role_id}")
async def revoke(user_id: str, role_id: str, ctx=require("rbac:write")):
    async def perform():
        await ctx.db.execute(delete(UserRoleGrant).where(UserRoleGrant.user_id == user_id,
                                                        UserRoleGrant.role_id == role_id))
        return {"user_id": user_id, "role_id": role_id, "status": "revoked"}

    return await command(ctx, "role.revoke", payload={"user_id": user_id, "role_id": role_id}, action=perform)
