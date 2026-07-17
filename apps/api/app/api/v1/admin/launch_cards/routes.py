from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.user import User
from app.services.launch_card.service import LaunchCardService

router = APIRouter(dependencies=[Depends(require_admin)])


class LaunchCardCreate(BaseModel):
    title: str
    change_summary: str = ""
    expected_metrics: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class LaunchCardMeasure(BaseModel):
    measured_metrics: dict[str, Any]
    status: str = "measured"


@router.get("")
async def list_cards(db: DbSession, _user: User = Depends(require_admin)) -> list[dict]:
    rows = await LaunchCardService(db).list_cards()
    return [_ser(r) for r in rows]


@router.post("")
async def create_card(
    body: LaunchCardCreate,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    card = await LaunchCardService(db).create(
        title=body.title,
        change_summary=body.change_summary,
        expected_metrics=body.expected_metrics,
        created_by=user.id,
        notes=body.notes,
    )
    return _ser(card)


@router.post("/{card_id}/measure")
async def measure_card(
    card_id: str,
    body: LaunchCardMeasure,
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    try:
        card = await LaunchCardService(db).fill_measured(
            card_id, body.measured_metrics, status=body.status
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _ser(card)


def _ser(r) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "change_summary": r.change_summary,
        "status": r.status,
        "expected_metrics": r.expected_metrics,
        "measured_metrics": r.measured_metrics,
        "notes": r.notes,
        "created_by": r.created_by,
    }
