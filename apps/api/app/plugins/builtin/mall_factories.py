"""Commerce factories, kept separate from the existing customer-service catalog."""

from app.plugins.builtin.mall_account import MallAccountPlugin
from app.plugins.builtin.mall_catalog import MallCatalogPlugin
from app.plugins.builtin.mall_inventory import MallInventoryPlugin
from app.plugins.builtin.mall_order import MallOrderPlugin
from app.plugins.builtin.mall_payment import MallPaymentPlugin
from app.plugins.builtin.mall_wallet import MallWalletPlugin
from app.plugins.builtin.mall_referral import MallReferralPlugin
from app.plugins.builtin.mall_notify import MallNotifyPlugin
from app.plugins.builtin.mall_support import MallSupportPlugin
from app.plugins.builtin.mall_admin import MallAdminPlugin
from app.plugins.builtin.mall_core import MallCorePlugin

MALL_FACTORIES = {
    "mall_core": MallCorePlugin,
    "mall_admin": MallAdminPlugin,
    "mall_account": MallAccountPlugin,
    "mall_catalog": MallCatalogPlugin,
    "mall_inventory": MallInventoryPlugin,
    "mall_order": MallOrderPlugin,
    "mall_payment": MallPaymentPlugin,
    "mall_wallet": MallWalletPlugin,
    "mall_referral": MallReferralPlugin,
    "mall_notify": MallNotifyPlugin,
    "mall_support": MallSupportPlugin,
}

