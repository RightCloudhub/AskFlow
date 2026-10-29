"""Resolve optional domain service ports without implicit plugin activation."""

from importlib import import_module

from app.commerce.core.errors import MallError
from app.plugins.runtime import require_app_context

FACTORIES = {
    "order": "OrderService", "payment": "PaymentService", "wallet": "WalletService",
    "catalog": "CatalogService", "inventory": "InventoryService", "referral": "ReferralService",
}


def enabled(module: str) -> bool:
    return require_app_context().enabled("mall_" + module)


def service(module: str, db):
    if not enabled(module):
        raise MallError("capability_unavailable", status=503)
    return getattr(import_module("app.commerce." + module + ".service"), FACTORIES[module])(db)
