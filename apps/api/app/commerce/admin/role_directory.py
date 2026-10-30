"""Minimal account and grant projections for the role administration workspace."""

from fastapi import APIRouter
from sqlalchemy import select

from app.commerce.admin.models import AdminRole, RolePermission, UserRoleGrant
from app.commerce.admin.permissions import require
from app.commerce.core.constants import PAGE_SIZE
from app.models.user import User

router = APIRouter()
RBAC_WRITE = require("rbac:write")


async def role_rows(db):
    roles = list(await db.scalars(select(AdminRole).order_by(AdminRole.code)))
    grants = await db.execute(select(RolePermission.role_id, RolePermission.permission_code))
    permissions = {}
    for role_id, permission in grants:
        permissions.setdefault(role_id, []).append(permission)
    return [{"id": role.id, "code": role.code, "name": role.name,
             "builtin": role.builtin, "version": role.version,
             "permissions": sorted(permissions.get(role.id, []))} for role in roles]


@router.get("/roles/users")
async def users(cursor: str = "", ctx=RBAC_WRITE):
    query = select(User.id, User.username).where(User.id > cursor, User.is_active)
    rows = list(await ctx.db.execute(query.order_by(User.id).limit(PAGE_SIZE + 1)))
    return {"items": [{"id": row.id, "username": row.username} for row in rows[:PAGE_SIZE]],
            "next_cursor": rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None}


@router.get("/roles/grants")
async def grants(cursor: str = "", ctx=RBAC_WRITE):
    query = select(UserRoleGrant, User.username, AdminRole.name).join(
        User, User.id == UserRoleGrant.user_id).join(
        AdminRole, AdminRole.id == UserRoleGrant.role_id).where(UserRoleGrant.id > cursor)
    rows = list(await ctx.db.execute(query.order_by(UserRoleGrant.id).limit(PAGE_SIZE + 1)))
    return {"items": [{"id": grant.id, "user_id": grant.user_id, "role_id": grant.role_id,
                       "username": username, "name": name, "title": f"{username} · {name}"}
                      for grant, username, name in rows[:PAGE_SIZE]],
            "next_cursor": rows[PAGE_SIZE - 1][0].id if len(rows) > PAGE_SIZE else None}
