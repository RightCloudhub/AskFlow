"""Lazy mall plugin router registration; disabled domains never mount admin routes."""

from importlib import import_module

from app.plugins.types import AdminNavItem

MALL_NAV_ORDER = 110


class MallPlugin:
    id = "mall"
    depends = ["mall_core"]
    module = ""
    label = ""
    has_admin = True

    def register(self, ctx):
        module = import_module("app.commerce." + self.module + ".api")
        ctx.api_router.include_router(module.router, prefix="/mall/" + self.module, tags=[self.id])
        if self.has_admin:
            admin = import_module("app.commerce." + self.module + ".admin_api")
            ctx.admin_router.include_router(admin.router, prefix="/mall/" + self.module, tags=[self.id])
            ctx.add_nav(AdminNavItem(self.id, "/admin/mall/" + self.module, self.label, MALL_NAV_ORDER))
