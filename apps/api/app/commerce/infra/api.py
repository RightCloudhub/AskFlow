"""Secret-free operations matrix, liveness and dependency readiness endpoints."""

from http import HTTPStatus

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.commerce.infra.health import port_matrix
from app.commerce.infra.matrix import capability_matrix
from app.core.config import get_settings
from app.core.deps import require_agent_or_admin

router = APIRouter()
health_router = APIRouter()
ADMIN_USER = Depends(require_agent_or_admin)


@router.get("")
async def infrastructure(_user=ADMIN_USER):
    return capability_matrix(get_settings())


@health_router.get("/health/live")
async def live():
    return {"status": "ok"}


@health_router.get("/health/ready")
async def ready():
    matrix = await port_matrix()
    status = HTTPStatus.OK if matrix["status"] == "ok" else HTTPStatus.SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status, content=matrix)
