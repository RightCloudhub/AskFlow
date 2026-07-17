"""Static proof that web MVP surfaces exist and are feature-gated (PRD §12.1 #16)."""

from pathlib import Path

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
    assert "FeaturesProvider" in app
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
    assert "useFeatures" in chat
    assert 'enabled("ticket")' in chat


def test_admin_pages_call_real_apis():
    docs = (WEB / "pages" / "admin" / "DocumentsPage.tsx").read_text(encoding="utf-8")
    assert "/api/v1/embedding/upload" in docs
    assert "/api/v1/admin/documents" in docs
    handoffs = (WEB / "pages" / "admin" / "HandoffsPage.tsx").read_text(encoding="utf-8")
    assert "/api/v1/admin/handoffs" in handoffs
    chat = (WEB / "pages" / "user" / "ChatPage.tsx").read_text(encoding="utf-8")
    assert "/api/v1/chat/conversations" in chat
    teams = (WEB / "pages" / "admin" / "TeamsPage.tsx").read_text(encoding="utf-8")
    assert "/api/v1/admin/teams" in teams
    sla = (WEB / "pages" / "admin" / "SlaPage.tsx").read_text(encoding="utf-8")
    assert "/api/v1/admin/sla/scan" in sla
    assert "/api/v1/admin/sla/status" in sla
    runs = (WEB / "pages" / "admin" / "AgentRunsPage.tsx").read_text(encoding="utf-8")
    assert "/api/v1/admin/agent-runs" in runs
    widget = (WEB / "pages" / "widget" / "WidgetPage.tsx").read_text(encoding="utf-8")
    assert "/widget/session" in widget
    assert "/widget/conversations/" in widget
    qc = (WEB / "pages" / "admin" / "QcPage.tsx").read_text(encoding="utf-8")
    assert "/api/v1/admin/qc/summary" in qc
    assert "/api/v1/admin/qc/low-quality" in qc
