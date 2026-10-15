"""Route names, reply copy and the router action DTO (arch §4.3)."""

from dataclasses import dataclass

from app.services.agent.pipeline.context import PipelineResult

ROUTE_CONTROL = "CONTROL"
ROUTE_TASK_RESUME = "TASK_RESUME"
ROUTE_TASK_CREATE = "TASK_CREATE"
ROUTE_CLARIFY = "CLARIFY"
ROUTE_STEP_UP = "STEP_UP"
ROUTE_INTERACTIVE = "INTERACTIVE"
ROUTE_REFUSE = "REFUSE"
ROUTE_HANDOFF = "HANDOFF"

PENDING_STEP_UP_KEY = "pending_step_up"
PENDING_TEXT_MAX = 500
CONFIRM_WORDS = ("确认", "同意", "好的", "可以", "confirm", "yes", "ok", "okay")
CANCEL_ACK = "已为您取消该任务。如需继续办理，请重新提出。"
CANCEL_BLOCKED_ACK = "该任务已转交人工或已结束，无法自动取消。"
CONFIRM_QUESTION = "该操作需要您的确认。回复「确认」以继续，或回复「取消」放弃。"
CONFIRM_EXPIRED = "确认已过期或无效，请重新发起办理。"
CONFIRM_ACK = "已收到确认，正在继续办理。"
RESUME_ACK = "已收到您的补充信息，正在继续处理。"
RELATED_ACK = "该请求正在处理中，进展会显示在本会话中。"
STEP_UP_REPLY = "为保护您的账户安全，请先完成身份验证：验证码已发送，请直接回复验证码。"
STEP_UP_CODE_HINT = "（测试验证码：{code}）"
STEP_UP_BAD_CODE = "验证码不正确，请重试。"
STEP_UP_EXPIRED = "验证已失效，请重新发起办理。"
CLARIFY_GOAL = "您是想办理「{goal}」吗？请补充说明或确认您的需求。"
REMINDER = "（提示：您的任务「{goal}」仍在处理中，如需取消请回复「取消」。）"


@dataclass
class RouterAction:
    route: str
    handled: PipelineResult | None = None
    reminder: str | None = None
    relation: str | None = None
