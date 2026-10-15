"""Authenticated facts management: view and forget (arch §4.8 user controls)."""

from fastapi import APIRouter, HTTPException, Query, status

from app.core import database
from app.core.deps import CurrentUser
from app.services.agent.identity import customer_scope
from app.services.agent.memory.facts import FactStore, FactView
from app.services.agent.memory.store import MemoryConflict

router = APIRouter()


@router.get("", response_model=list[FactView])
async def list_memories(user: CurrentUser):
    views = await FactStore(database.SessionLocal).list(customer_scope(user.id))
    return [view for view in views if view.status == "active"]


@router.delete("/{key}", response_model=FactView)
async def forget_memory(key: str, user: CurrentUser, *, expected_version: int = Query(ge=1)):
    try:
        return await FactStore(database.SessionLocal).delete(
            customer_scope(user.id), key, expected_version=expected_version
        )
    except MemoryConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "memory_version_conflict") from exc


@router.post("/forget-all")
async def forget_all(user: CurrentUser):
    store = FactStore(database.SessionLocal)
    scope = customer_scope(user.id)
    forgotten: list[str] = []
    for view in await store.list(scope):
        if view.status != "active":
            continue
        try:
            await store.delete(scope, view.key, expected_version=view.version)
            forgotten.append(view.key)
        except MemoryConflict:
            continue
    return {"forgotten": forgotten}
