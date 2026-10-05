"""Notification operations are independent of business writes and honor channel health."""

from typing import Literal

from pydantic import Field

from app.services.agent.domains.receipts import connector_receipt
from app.services.agent.intake.goals import GOAL_NOTIFICATION
from app.services.agent.service.contracts import Candidate, Operation, OperationCall, Record
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent

NOTIFY_GOAL = GOAL_NOTIFICATION
NOTIFY_CHAT = "notify.send.chat"
NOTIFY_EMAIL = "notify.send.email"
NOTIFY_PERMISSION = "notifications.send"
CHANNELS = {NOTIFY_CHAT: "chat", NOTIFY_EMAIL: "email"}
PREFERRED_PRIORITY = 0
FALLBACK_PRIORITY = 1


class NotifyInput(Record):
    conversation_id: str = Field(min_length=1)
    channel: Literal["chat", "email"]
    message: str = Field(min_length=1)


def channel_available(args, env, *, channel: str) -> bool:
    capability = env.facts.get("channels", {}).get(channel, {})
    return (
        args.channel == channel
        and capability.get("capable") is True
        and capability.get("health") == "ok"
    )


def notify_operations(*, sender) -> list[Operation]:
    async def send(call):
        result = await sender(call)
        receipt = connector_receipt(call, result, source="notification_channel")
        if receipt.status == "succeeded" and not result.get("message_id"):
            raise ValueError("Notification receipt requires a message identifier")
        return receipt

    def operation(name, channel):
        return Operation(
            operation_id=name,
            version="1",
            effect="notify",
            permission=NOTIFY_PERMISSION,
            input_schema=NotifyInput,
            handler=send,
            precondition=lambda args, env: channel_available(args, env, channel=channel),
            compensation="irreversible:notification",
            replay_receipts_when_waiting=True,
        )

    return [operation(name, channel) for name, channel in CHANNELS.items()]


def notify_candidates(task, env) -> list[Candidate]:
    preferred = env.preferences.get("contact_channel", "chat")
    return [
        Candidate(
            call=OperationCall(
                operation_id=name,
                key=f"{task.task_id}:notify:{channel}",
                arguments={**task.inputs, "channel": channel},
            ),
            priority=PREFERRED_PRIORITY if channel == preferred else FALLBACK_PRIORITY,
            reason=f"Contact channel {channel}; preference={preferred} ({env.preference_status})",
        )
        for name, channel in CHANNELS.items()
    ]


def verify_notify(task, env) -> bool:
    if task.completion_condition != NOTIFY_GOAL or NOTIFY_PERMISSION not in env.permissions:
        return False
    return any(
        e.operation_id in CHANNELS
        and e.source == "notification_channel"
        and bool(e.data.get("message_id"))
        for e in task.evidence
    )


def notify_agent(store, observe, *, sender):
    async def propose(task, env):
        return notify_candidates(task, env)

    return ServiceAgent(
        store,
        OperationRegistry(notify_operations(sender=sender)),
        AgentPolicy(observe=observe, propose=propose, verify=verify_notify),
    )
