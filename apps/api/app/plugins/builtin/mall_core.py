"""Commerce infrastructure and public discovery, conditionally assembled."""

import logging

from app.plugins.types import AdminNavItem

INFRA_NAV_ORDER = 96


class MallCorePlugin:
    id = "mall_core"
    depends = ["core"]

    def register(self, ctx):
        from app.commerce.core.api import router
        from app.commerce.infra.api import health_router
        from app.commerce.infra.api import router as admin_router
        from app.commerce.infra.runtime import Infra

        ctx.services["mall_infra"] = Infra(ctx.settings)
        ctx.api_router.include_router(router, prefix="/mall", tags=["mall"])
        ctx.admin_router.include_router(admin_router, prefix="/infra", tags=["infra"])
        ctx.root_router.include_router(health_router)
        ctx.add_nav(AdminNavItem(self.id, "/admin/infra", "基础设施", INFRA_NAV_ORDER))

    async def boot(self, ctx):
        from app.commerce.infra.matrix import capability_matrix
        from app.commerce.infra.startup import assert_adapter_configuration
        from app.commerce.infra.logging import configure

        ctx.settings.assert_commerce_safe()
        assert_adapter_configuration(ctx.settings)
        configure()
        logging.getLogger("askflow.mall").info("infrastructure=%s", capability_matrix(ctx.settings))

    async def shutdown(self, ctx):
        from app.commerce.infra.database import close_read_engines

        await close_read_engines(ctx)
        await ctx.services["mall_infra"].close()
