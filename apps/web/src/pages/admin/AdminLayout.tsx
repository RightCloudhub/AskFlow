import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Grid, Layout, Menu, Skeleton } from "antd";
import { getToken } from "../../api/client";
import { useFeatures } from "../../plugins/features";
import { useAdminMenu } from "./layout-menu";
import { AdminHeader, Sidebar } from "./layout-parts";
import { NavigationSearch } from "./navigation-search";
import { AdminAccessGate } from "../../admin/AdminAccessGate";

const COLLAPSE_KEY = "askflow_admin_sider_collapsed";
const PLACEHOLDER_ROWS = 8;

function readCollapsed() {
  try { return localStorage.getItem(COLLAPSE_KEY) === "1"; }
  catch { return false; }
}

function rememberCollapsed(collapsed: boolean) {
  try { localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0"); }
  catch { /* Navigation remains usable when storage is unavailable. */ }
}

export function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const mobile = screens.lg === false;
  const { ready } = useFeatures();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [drawer, setDrawer] = useState(false);
  const { items, selected, crumb, workspace, sections, activeGroup } = useAdminMenu(location.pathname);
  const [openKeys, setOpenKeys] = useState<string[]>([]);
  useEffect(() => { rememberCollapsed(collapsed); }, [collapsed]);
  useEffect(() => { setDrawer(false); }, [location.pathname]);
  useEffect(() => { if (activeGroup) setOpenKeys((keys) => keys.includes(activeGroup) ? keys : [...keys, activeGroup]); }, [activeGroup]);
  if (!getToken()) return <Navigate to="/login" replace />;
  const menu = ready ? <Menu mode="inline" selectedKeys={[selected]} items={items}
    openKeys={collapsed && !mobile ? undefined : openKeys} onOpenChange={setOpenKeys}
    onClick={({ key }) => navigate(String(key))} className="af-pro-menu" /> :
    <div className="af-pro-loading"><Skeleton paragraph={{ rows: PLACEHOLDER_ROWS }} title={false} /></div>;
  return <Layout className="af-pro-layout">
    <Sidebar {...{ mobile, collapsed, drawer, menu, setCollapsed, setDrawer }} />
    <Layout className="af-pro-main"><AdminHeader {...{ mobile, workspace, crumb }}
      search={<NavigationSearch sections={sections} />} openDrawer={() => setDrawer(true)} />
      <Layout.Content className="af-pro-content"><AdminAccessGate><Outlet /></AdminAccessGate></Layout.Content></Layout>
  </Layout>;
}
