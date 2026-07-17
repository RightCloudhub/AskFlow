"""Built-in capability plugins (register-time wiring only)."""

from __future__ import annotations

from typing import Any

from app.plugins.builtin.agent import AgentPlugin
from app.plugins.builtin.analytics import AnalyticsPlugin
from app.plugins.builtin.connectors import ConnectorsPlugin
from app.plugins.builtin.core import CorePlugin
from app.plugins.builtin.cost import CostPlugin
from app.plugins.builtin.handoff import HandoffPlugin
from app.plugins.builtin.knowledge import KnowledgePlugin
from app.plugins.builtin.launch import LaunchPlugin
from app.plugins.builtin.mcp import McpPlugin
from app.plugins.builtin.notify import NotifyPlugin
from app.plugins.builtin.ops import OpsPlugin
from app.plugins.builtin.rag import RagPlugin
from app.plugins.builtin.sla import SlaPlugin
from app.plugins.builtin.sso import SsoPlugin
from app.plugins.builtin.teams import TeamsPlugin
from app.plugins.builtin.ticket import TicketPlugin
from app.plugins.builtin.tools import ToolsPlugin
from app.plugins.builtin.feishu import FeishuPlugin
from app.plugins.builtin.qc import QcPlugin
from app.plugins.builtin.widget import WidgetPlugin

# Factory map: id → instance
BUILTIN_FACTORIES: dict[str, type] = {
    "core": CorePlugin,
    "rag": RagPlugin,
    "agent": AgentPlugin,
    "tools": ToolsPlugin,
    "ticket": TicketPlugin,
    "handoff": HandoffPlugin,
    "knowledge": KnowledgePlugin,
    "ops": OpsPlugin,
    "cost": CostPlugin,
    "sla": SlaPlugin,
    "notify": NotifyPlugin,
    "sso": SsoPlugin,
    "teams": TeamsPlugin,
    "connectors": ConnectorsPlugin,
    "launch": LaunchPlugin,
    "analytics": AnalyticsPlugin,
    "mcp": McpPlugin,
    "widget": WidgetPlugin,
    "feishu": FeishuPlugin,
    "qc": QcPlugin,
}


def create_builtin(plugin_id: str) -> Any:
    cls = BUILTIN_FACTORIES.get(plugin_id)
    if cls is None:
        raise KeyError(f"No builtin plugin for {plugin_id!r}")
    return cls()
