"""账号 plugin, assembled only when enabled."""

from app.plugins.builtin.mall_base import MallPlugin


class MallAccountPlugin(MallPlugin):
    id = "mall_account"
    depends = ["mall_core"]
    module = "account"
    label = "账号"

