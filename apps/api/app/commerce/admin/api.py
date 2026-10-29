"""Current-user permissions for feature and button visibility."""

from fastapi import APIRouter

from app.commerce.admin.permissions import permissions_for
from app.commerce.core.deps import MallContext

router = APIRouter()


@router.get("/permissions")
async def permissions(ctx: MallContext):
    return {"permissions": sorted(await permissions_for(ctx.db, ctx.user))}
