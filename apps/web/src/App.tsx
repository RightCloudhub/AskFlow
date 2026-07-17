import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api/client";
import { FeaturesProvider, useFeatures } from "./plugins/features";
import { filterRoutes } from "./plugins/registry";
import { LoginPage } from "./pages/auth/LoginPage";
import { ChatPage } from "./pages/user/ChatPage";
import { TicketsPage } from "./pages/user/TicketsPage";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { DashboardPage } from "./pages/admin/DashboardPage";
import { DocumentsPage } from "./pages/admin/DocumentsPage";
import { IntentsPage } from "./pages/admin/IntentsPage";
import { PromptsPage } from "./pages/admin/PromptsPage";
import { GapsPage } from "./pages/admin/GapsPage";
import { DraftsPage } from "./pages/admin/DraftsPage";
import { HandoffsPage } from "./pages/admin/HandoffsPage";
import { TicketsAdminPage } from "./pages/admin/TicketsAdminPage";
import { AuditPage } from "./pages/admin/AuditPage";
import { UsersPage } from "./pages/admin/UsersPage";
import { ConnectorsPage } from "./pages/admin/ConnectorsPage";
import { CostsPage } from "./pages/admin/CostsPage";
import { LaunchCardsPage } from "./pages/admin/LaunchCardsPage";
import { TeamsPage } from "./pages/admin/TeamsPage";
import { SlaPage } from "./pages/admin/SlaPage";
import { AgentRunsPage } from "./pages/admin/AgentRunsPage";
import { WidgetPage } from "./pages/widget/WidgetPage";
import { QcPage } from "./pages/admin/QcPage";

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

function AppRoutes() {
  const { features, enabled } = useFeatures();
  const adminRoutes = filterRoutes(features);
  const showTickets = enabled("ticket");

  return (
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
  );
}

export function App() {
  return (
    <FeaturesProvider>
      <AppRoutes />
    </FeaturesProvider>
  );
}
