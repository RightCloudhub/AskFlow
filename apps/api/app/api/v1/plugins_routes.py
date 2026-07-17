"""Public plugin/features discovery (admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import require_agent_or_admin
from app.models.user import User
from app.plugins.loader import features_public_view
from app.plugins.runtime import get_app_context

router = APIRouter()


@router.get("")
async def list_features(
    _user: User = Depends(require_agent_or_admin),
) -> dict:
    ctx = get_app_context()
    if ctx is None:
        return {
            "profile": "unknown",
            "features": [],
            "loaded": [],
            "admin_nav": [],
            "route_handlers": [],
            "side_effects": [],
        }
    return features_public_view(ctx)
