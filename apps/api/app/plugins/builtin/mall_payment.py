"""支付 plugin, assembled only when enabled."""

from app.plugins.builtin.mall_base import MallPlugin


class MallPaymentPlugin(MallPlugin):
    id = "mall_payment"
    depends = ["mall_order"]
    module = "payment"
    label = "支付"

