"""Settings for the chat-to-task integration, kept separate from legacy settings."""

from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.services.agent.intake.goals import GOAL_ORDER_STATUS, GOAL_SPECS

DEFAULT_POLL_SECONDS = 5.0


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="SERVICE_TASKS_ENABLED")
    goals: Annotated[frozenset[str], NoDecode] = Field(
        default=frozenset({GOAL_ORDER_STATUS}), validation_alias="SERVICE_TASKS_GOALS"
    )
    poll_seconds: float = Field(
        default=DEFAULT_POLL_SECONDS, ge=1, validation_alias="SERVICE_TASK_POLL_SECONDS"
    )

    @field_validator("goals", mode="before")
    @classmethod
    def parse_goals(cls, value):
        aliases = {spec.namespace: goal for goal, spec in GOAL_SPECS.items()}
        if isinstance(value, str):
            return frozenset(
                aliases.get(item.strip(), item.strip()) for item in value.split(",") if item.strip()
            )
        return value

    def takes_over(self, goal: str | None) -> bool:
        return self.enabled and goal in self.goals
