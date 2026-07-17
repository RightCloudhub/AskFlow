"""Production secret fail-safe (S-01)."""

import pytest

from app.core.config import Settings


def test_dev_allows_weak_secret():
    s = Settings(ASKFLOW_ENV="development", SECRET_KEY="change-me-in-production")
    s.assert_startup_safe()  # should not raise


def test_production_rejects_weak_secret():
    s = Settings(ASKFLOW_ENV="production", SECRET_KEY="change-me-in-production")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        s.assert_startup_safe()
