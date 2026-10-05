"""Compatibility entry point; goal intake now lives under the agent package."""

from app.services.agent.intake.chat import maybe_create_goal_task as maybe_create_order_task

__all__ = ["maybe_create_order_task"]
