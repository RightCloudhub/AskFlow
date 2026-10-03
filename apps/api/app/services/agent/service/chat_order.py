"""Compatibility import for the consolidated order domain."""

import sys

from app.services.agent.domains import order

sys.modules[__name__] = order
