"""通知 plugin, assembled only when enabled."""

from app.plugins.builtin.mall_base import MallPlugin


class MallNotifyPlugin(MallPlugin):
    id = "mall_notify"
    depends = ["mall_core","notify"]
    module = "notify"
    label = "通知"

