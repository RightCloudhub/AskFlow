"""P3 (M4): SERVICE_TASKS_GOALS gates which goals the new runtime takes over."""

from app.services.agent.intake.goals import GOAL_ORDER_STATUS, GOAL_TICKET_RESOLUTION
from app.services.agent.service.settings import ServiceSettings


def test_default_takeover_list_contains_only_order(monkeypatch):
    monkeypatch.delenv("SERVICE_TASKS_GOALS", raising=False)
    settings = ServiceSettings()
    assert settings.goals == frozenset({GOAL_ORDER_STATUS})
    assert settings.takes_over(GOAL_ORDER_STATUS)
    assert not settings.takes_over(GOAL_TICKET_RESOLUTION)


def test_takeover_list_parses_comma_separated_env(monkeypatch):
    monkeypatch.setenv("SERVICE_TASKS_GOALS", f" {GOAL_ORDER_STATUS} , {GOAL_TICKET_RESOLUTION} ")
    settings = ServiceSettings()
    assert settings.goals == frozenset({GOAL_ORDER_STATUS, GOAL_TICKET_RESOLUTION})
    assert settings.takes_over(GOAL_TICKET_RESOLUTION)


def test_empty_takeover_list_disables_all_goals(monkeypatch):
    monkeypatch.setenv("SERVICE_TASKS_GOALS", "")
    settings = ServiceSettings()
    assert settings.goals == frozenset()
    assert not settings.takes_over(GOAL_ORDER_STATUS)
