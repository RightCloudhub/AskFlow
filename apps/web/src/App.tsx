import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Spin } from "antd";
import { getToken } from "./api/client";
import { useFeatures } from "./plugins/features";
import { filterRoutes } from "./plugins/registry";

const LoginPage = lazy(() =>
  import("./pages/auth/LoginPage").then((m) => ({ default: m.LoginPage })),
);
const ChatPage = lazy(() =>
  import("./pages/user/ChatPage").then((m) => ({ default: m.ChatPage })),
);
const TicketsPage = lazy(() =>
  import("./pages/user/TicketsPage").then((m) => ({ default: m.TicketsPage })),
);
const WidgetPage = lazy(() =>
  import("./pages/widget/WidgetPage").then((m) => ({ default: m.WidgetPage })),
);
const AdminLayout = lazy(() =>
  import("./pages/admin/AdminLayout").then((m) => ({ default: m.AdminLayout })),
);
const DashboardPage = lazy(() =>
  import("./pages/admin/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const DocumentsPage = lazy(() =>
  import("./pages/admin/DocumentsPage").then((m) => ({ default: m.DocumentsPage })),
);
const IntentsPage = lazy(() =>
  import("./pages/admin/IntentsPage").then((m) => ({ default: m.IntentsPage })),
);
const PromptsPage = lazy(() =>
  import("./pages/admin/PromptsPage").then((m) => ({ default: m.PromptsPage })),
);
const GapsPage = lazy(() =>
  import("./pages/admin/GapsPage").then((m) => ({ default: m.GapsPage })),
);
const DraftsPage = lazy(() =>
  import("./pages/admin/DraftsPage").then((m) => ({ default: m.DraftsPage })),
);
const HandoffsPage = lazy(() =>
  import("./pages/admin/HandoffsPage").then((m) => ({ default: m.HandoffsPage })),
);
const TicketsAdminPage = lazy(() =>
  import("./pages/admin/TicketsAdminPage").then((m) => ({
    default: m.TicketsAdminPage,
  })),
);
const AuditPage = lazy(() =>
  import("./pages/admin/AuditPage").then((m) => ({ default: m.AuditPage })),
);
const UsersPage = lazy(() =>
  import("./pages/admin/UsersPage").then((m) => ({ default: m.UsersPage })),
);
const ConnectorsPage = lazy(() =>
  import("./pages/admin/ConnectorsPage").then((m) => ({ default: m.ConnectorsPage })),
);
const CostsPage = lazy(() =>
  import("./pages/admin/CostsPage").then((m) => ({ default: m.CostsPage })),
);
const LaunchCardsPage = lazy(() =>
  import("./pages/admin/LaunchCardsPage").then((m) => ({
    default: m.LaunchCardsPage,
  })),
);
const TeamsPage = lazy(() =>
  import("./pages/admin/TeamsPage").then((m) => ({ default: m.TeamsPage })),
);
const SlaPage = lazy(() =>
  import("./pages/admin/SlaPage").then((m) => ({ default: m.SlaPage })),
);
const AgentRunsPage = lazy(() =>
  import("./pages/admin/AgentRunsPage").then((m) => ({ default: m.AgentRunsPage })),
);
const QcPage = lazy(() =>
  import("./pages/admin/QcPage").then((m) => ({ default: m.QcPage })),
);

const PAGE_MAP: Record<string, React.ReactNode> = {
  dashboard: <DashboardPage />,
  qc: <QcPage />,
  documents: <DocumentsPage />,
  intents: <IntentsPage />,
  prompts: <PromptsPage />,
  gaps: <GapsPage />,
  drafts: <DraftsPage />,
  handoffs: <HandoffsPage />,
  tickets: <TicketsAdminPage />,
  teams: <TeamsPage />,
  sla: <SlaPage />,
  audit: <AuditPage />,
  users: <UsersPage />,
  connectors: <ConnectorsPage />,
  costs: <CostsPage />,
  "launch-cards": <LaunchCardsPage />,
  "agent-runs": <AgentRunsPage />,
};

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PageFallback() {
  return (
    <div className="af-query-state" style={{ minHeight: "40vh" }}>
      <Spin tip="加载页面…" />
    </div>
  );
}

function AppRoutes() {
  const { features, enabled } = useFeatures();
  const adminRoutes = filterRoutes(features);
  const showTickets = enabled("ticket");

  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/widget" element={<WidgetPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <ChatPage />
            </RequireAuth>
          }
        />
        {showTickets ? (
          <Route
            path="/tickets"
            element={
              <RequireAuth>
                <TicketsPage />
              </RequireAuth>
            }
          />
        ) : null}
        <Route
          path="/admin"
          element={
            <RequireAuth>
              <AdminLayout />
            </RequireAuth>
          }
        >
          {adminRoutes.map((r) => (
            <Route
              key={r.path || "index"}
              index={r.path === ""}
              path={r.path || undefined}
              element={PAGE_MAP[r.page] ?? <Navigate to="/admin" replace />}
            />
          ))}
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export function App() {
  return <AppRoutes />;
}
