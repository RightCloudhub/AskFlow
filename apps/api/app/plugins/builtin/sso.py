"""OIDC SSO admin routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class SsoPlugin:
    id = "sso"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.sso.routes import router as sso_router

        ctx.admin_router.include_router(sso_router, prefix="/sso", tags=["sso"])
