from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, require_admin
from app.models.user import User
from app.services.agent.cost.store import CostStore

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/summary")
async def cost_summary(db: DbSession, _user: User = Depends(require_admin)) -> dict:
    return await CostStore(db).aggregate()
