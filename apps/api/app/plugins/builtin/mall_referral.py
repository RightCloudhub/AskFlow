"""邀请与风控 plugin, assembled only when enabled."""

from app.plugins.builtin.mall_base import MallPlugin


class MallReferralPlugin(MallPlugin):
    id = "mall_referral"
    depends = ["mall_wallet"]
    module = "referral"
    label = "邀请与风控"

