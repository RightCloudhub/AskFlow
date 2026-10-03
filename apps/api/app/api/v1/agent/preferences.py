"""Authenticated self-service memory management; scope is never accepted from request data."""

from fastapi import APIRouter, HTTPException, Query, status

from app.core import database
from app.core.deps import CurrentUser
from app.services.agent.memory.contracts import (
    PreferenceChange, PreferenceKey, PreferenceView,
)
from app.services.agent.memory.store import MemoryConflict, PreferenceStore
from app.services.agent.identity import customer_scope

router = APIRouter()


@router.get("", response_model=list[PreferenceView])
async def list_preferences(user: CurrentUser):
    return await PreferenceStore(database.SessionLocal).list(customer_scope(user.id))


@router.put("", response_model=PreferenceView)
async def put_preference(payload: PreferenceChange, user: CurrentUser):
    try:
        return await PreferenceStore(database.SessionLocal).put(customer_scope(user.id), payload)
    except MemoryConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "preference_version_conflict") from exc


@router.delete("/{key}", response_model=PreferenceView)
async def delete_preference(key: PreferenceKey, user: CurrentUser, *,
                            expected_version: int = Query(ge=1)):
    try:
        return await PreferenceStore(database.SessionLocal).delete(
            customer_scope(user.id), key, expected_version=expected_version,
        )
    except MemoryConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "preference_version_conflict") from exc
