"""钱包 plugin, assembled only when enabled."""

from app.plugins.builtin.mall_base import MallPlugin


class MallWalletPlugin(MallPlugin):
    id = "mall_wallet"
    depends = ["mall_account"]
    module = "wallet"
    label = "钱包"

    def register(self, ctx):
        from app.commerce.wallet.immutability import install

        super().register(ctx)
        install()

