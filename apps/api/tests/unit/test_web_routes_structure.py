"""Static proof that web MVP surfaces exist and are feature-gated (PRD §12.1 #16)."""

from pathlib import Path

import pytest

# tests/unit -> api -> apps -> web/src
WEB = Path(__file__).resolve().parents[3] / "web" / "src"


def test_user_and_admin_routes_exist():
    app = (WEB / "App.tsx").read_text(encoding="utf-8")
    for route in [
        "/login",
        "/widget",
        "/tickets",
        "/admin",
        "documents",
        "intents",
        "prompts",
        "gaps",
        "drafts",
        "handoffs",
        "audit",
        "users",
        "connectors",
        "costs",
        "launch-cards",
        "teams",
        "sla",
        "agent-runs",
        "qc",
    ]:
        assert route in app, f"missing route {route}"


def test_frontend_feature_gated_assembly():
    """UI filters nav/routes by same enablement notion as API plugins."""
    app = (WEB / "App.tsx").read_text(encoding="utf-8")
    main = (WEB / "main.tsx").read_text(encoding="utf-8")
    assert '<AppProviders>' in main and '</AppProviders>' in main
    assert main.index('<AppProviders>') < main.index('<App />')
    assert main.index('<App />') < main.index('</AppProviders>')
    providers = (WEB / "providers" / "AppProviders.tsx").read_text(encoding="utf-8")
    assert "<FeaturesProvider>{children}</FeaturesProvider>" in providers
    assert "filterRoutes" in app
    assert "enabled(" in app or 'enabled("ticket")' in app
    layout = (WEB / "pages" / "admin" / "AdminLayout.tsx").read_text(encoding="utf-8")
    assert "filterNav" in layout
    assert "useFeatures" in layout
    registry = (WEB / "plugins" / "registry.ts").read_text(encoding="utf-8")
    assert "filterNav" in registry
    assert "filterRoutes" in registry
    assert "CORE_FEATURES" in registry
    features = (WEB / "plugins" / "features.tsx").read_text(encoding="utf-8")
    assert "/api/v1/admin/features" in features
    # AC4 fail-closed: discovery error must not enable full catalog
    assert "CORE_FEATURES" in features
    assert "DEFAULT_FEATURES" not in features
    chat = (WEB / "pages" / "user" / "ChatPage.tsx").read_text(encoding="utf-8")
    assert "<AppShell" in chat
    shell = (WEB / "components" / "layout" / "AppShell.tsx").read_text(encoding="utf-8")
    assert "useFeatures" in shell
    assert 'enabled("ticket")' in shell


# Pages delegate through query hooks to services after the web refactor.
# Verify imports as well as endpoint strings in their owning modules.
@pytest.mark.parametrize("case", [
    ("admin/DocumentsPage", "use-documents", "document-service", (
        "/api/v1/embedding/upload", "/api/v1/admin/documents",
    )),
    ("admin/HandoffsPage", "use-ops", "handoff-service", (
        "/api/v1/admin/handoffs",
    )),
    ("user/ChatPage", "use-chat", "chat-service", (
        "/api/v1/chat/conversations",
    )),
    ("admin/TeamsPage", "use-ops", "team-service", ("/api/v1/admin/teams",)),
    ("admin/SlaPage", "use-ops", "sla-service", (
        "/api/v1/admin/sla/scan", "/api/v1/admin/sla/status",
    )),
    ("admin/AgentRunsPage", "use-governance", "agent-run-service", (
        "/api/v1/admin/agent-runs",
    )),
    ("admin/QcPage", "use-governance", "qc-service", (
        "/api/v1/admin/qc/summary", "/api/v1/admin/qc/low-quality",
    )),
], ids=["documents", "handoffs", "chat", "teams", "sla", "agent-runs", "qc"])
def test_pages_connect_to_real_apis(case):
    page_name, hook_name, service_name, endpoints = case
    page = (WEB / "pages" / f"{page_name}.tsx").read_text(encoding="utf-8")
    hook = (WEB / "hooks" / f"{hook_name}.ts").read_text(encoding="utf-8")
    service = (WEB / "services" / f"{service_name}.ts").read_text(encoding="utf-8")
    assert f'from "../../hooks/{hook_name}"' in page
    assert f'from "../services/{service_name}"' in hook
    assert 'from "../api/client"' in service
    for endpoint in endpoints:
        assert endpoint in service, f"{service_name} missing {endpoint}"


def test_widget_calls_real_apis():
    widget = (WEB / "pages" / "widget" / "WidgetPage.tsx").read_text(encoding="utf-8")
    assert "/widget/session" in widget
    assert "/widget/conversations/" in widget
