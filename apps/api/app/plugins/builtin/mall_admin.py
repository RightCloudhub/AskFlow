"""Fine-grained RBAC/configuration; each domain owns its administration service."""

from app.plugins.types import AdminNavItem

ADMIN_NAV_ORDER = 109


class MallAdminPlugin:
    id = "mall_admin"
    depends = ["mall_core"]

    def register(self, ctx):
        from app.commerce.admin.api import router
        from app.commerce.admin.admin_api import router as admin_router
        from app.commerce.admin.dashboard import router as dashboard_router

        ctx.api_router.include_router(router, prefix="/mall/admin", tags=[self.id])
        ctx.admin_router.include_router(admin_router, prefix="/mall", tags=[self.id])
        ctx.admin_router.include_router(dashboard_router, prefix="/mall", tags=[self.id])
        ctx.add_nav(AdminNavItem(self.id, "/admin/mall/settings", "商城配置与权限", ADMIN_NAV_ORDER))
