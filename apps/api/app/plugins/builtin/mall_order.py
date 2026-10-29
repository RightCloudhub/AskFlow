"""订单 plugin, assembled only when enabled."""

from app.plugins.builtin.mall_base import MallPlugin


class MallOrderPlugin(MallPlugin):
    id = "mall_order"
    depends = ["mall_inventory","mall_account"]
    module = "order"
    label = "订单"

    def register(self, ctx):
        from app.commerce.support.lookup import router

        super().register(ctx)
        ctx.root_router.include_router(router)

