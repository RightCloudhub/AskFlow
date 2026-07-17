"""Core plugin: auth, chat, health, audit, users, system/features."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class CorePlugin:
    id = "core"
    depends: list[str] = []

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.audit_logs.routes import router as audit_router
        from app.api.v1.admin.auth.routes import router as auth_router
        from app.api.v1.admin.system.routes import router as system_router
        from app.api.v1.admin.users.routes import router as users_router
        from app.api.v1.chat.routes import router as chat_router
        from app.api.v1.health.routes import router as health_router
        from app.api.v1.plugins_routes import router as features_router

        ctx.api_router.include_router(health_router, tags=["health"])
        ctx.api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
        ctx.admin_router.include_router(auth_router, prefix="/auth", tags=["auth"])
        ctx.admin_router.include_router(audit_router, prefix="/audit-logs", tags=["audit"])
        ctx.admin_router.include_router(system_router, prefix="/system", tags=["system"])
        ctx.admin_router.include_router(users_router, prefix="/users", tags=["users"])
        ctx.admin_router.include_router(features_router, prefix="/features", tags=["features"])
        ctx.add_nav(AdminNavItem("core", "/admin/audit", "审计", order=90))
        ctx.add_nav(AdminNavItem("core", "/admin/users", "用户", order=91))
