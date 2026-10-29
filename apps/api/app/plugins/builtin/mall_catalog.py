"""商品 plugin, assembled only when enabled."""

from app.plugins.builtin.mall_base import MallPlugin


class MallCatalogPlugin(MallPlugin):
    id = "mall_catalog"
    depends = ["mall_core"]
    module = "catalog"
    label = "商品"

