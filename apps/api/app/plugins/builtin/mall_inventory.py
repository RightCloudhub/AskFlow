"""库存 plugin, assembled only when enabled."""

from app.plugins.builtin.mall_base import MallPlugin


class MallInventoryPlugin(MallPlugin):
    id = "mall_inventory"
    depends = ["mall_catalog"]
    module = "inventory"
    label = "库存"

