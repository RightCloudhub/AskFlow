"""Register all schemas without enabling domain routes or workers."""

from importlib import import_module

MODEL_MODULES = [
  "app.commerce.core.models",
  "app.commerce.core.event_retry",
  "app.commerce.account.models",
  "app.commerce.catalog.models",
  "app.commerce.inventory.models",
  "app.commerce.order.models",
  "app.commerce.order.refund_models",
  "app.commerce.payment.models",
  "app.commerce.wallet.models",
  "app.commerce.wallet.operations_models",
  "app.commerce.wallet.reversal_models",
  "app.commerce.referral.models",
  "app.commerce.notify.models",
  "app.commerce.admin.models",
  "app.commerce.support.models"
]


def register_models():
    for name in MODEL_MODULES:
        import_module(name)


register_models()

