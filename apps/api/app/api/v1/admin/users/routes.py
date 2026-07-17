from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.user import User
from app.schemas.auth import UserOut
from app.services.users.admin import UserAdminService

router = APIRouter(dependencies=[Depends(require_admin)])


class ActiveBody(BaseModel):
    is_active: bool


@router.get("", response_model=list[UserOut])
async def list_users(db: DbSession, _user: User = Depends(require_admin)) -> list[UserOut]:
    rows = await UserAdminService(db).list_users()
    return [UserOut.model_validate(u) for u in rows]


@router.patch("/{user_id}/active", response_model=UserOut)
async def set_active(
    user_id: str,
    body: ActiveBody,
    db: DbSession,
    user: CurrentUser,
) -> UserOut:
    u = await UserAdminService(db).set_active(user_id, body.is_active, actor_id=user.id)
    return UserOut.model_validate(u)


@router.get("/{user_id}/export")
async def export_user(user_id: str, db: DbSession, _user: User = Depends(require_admin)) -> dict:
    return await UserAdminService(db).export_user_data(user_id)


@router.delete("/{user_id}/data")
async def delete_user_data(
    user_id: str,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    counts = await UserAdminService(db).delete_user_data(user_id, actor_id=user.id)
    return {"ok": True, "deleted": counts}
