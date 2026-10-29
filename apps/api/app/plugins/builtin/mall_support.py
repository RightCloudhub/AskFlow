"""商城客服 plugin, assembled only when enabled."""

from app.plugins.builtin.mall_base import MallPlugin


class MallSupportPlugin(MallPlugin):
    id = "mall_support"
    depends = ["mall_order","ticket","handoff"]
    module = "support"
    label = "商城客服"

    def register(self, ctx):
        from app.commerce.support.capabilities import CAPABILITIES

        super().register(ctx)
        if ctx.enabled("agent"):
            from app.services.agent.domains.refund import scoped_mall_refund_agent

            ctx.services["mall_capabilities"] = CAPABILITIES
            ctx.services["mall_refund_agent_factory"] = scoped_mall_refund_agent

