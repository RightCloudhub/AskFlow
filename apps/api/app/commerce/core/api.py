"""Public minimal mall discovery and validated object reads."""

from http import HTTPStatus

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

from app.commerce.core.errors import MallError
from app.commerce.infra.objects import LocalObjects
from app.commerce.infra.runtime import infra
from app.plugins.runtime import require_app_context

router = APIRouter()


@router.get("/features")
async def features():
    ctx = require_app_context()
    public = {pid for pid in ctx.features if pid.startswith("mall_")}
    public.update(ctx.features & {"ticket", "handoff", "agent"})
    return {"profile": ctx.settings.askflow_profile, "features": sorted(public),
            "demo_mailbox": ctx.settings.env == "development" and ctx.settings.mall_demo_mailbox_enabled}


@router.get("/files/{key}")
async def object_file(key: str):
    store = infra().objects
    if not isinstance(store, LocalObjects):
        return RedirectResponse(await store.url(key))
    path = store.path(key)
    if not path.is_file():
        raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff"})
