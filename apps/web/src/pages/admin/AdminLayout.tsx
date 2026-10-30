import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Grid, Layout, Menu, Skeleton } from "antd";
import { getToken } from "../../api/client";
import { useFeatures } from "../../plugins/features";
import { useAdminMenu } from "./layout-menu";
import { AdminHeader, Sidebar } from "./layout-parts";

const COLLAPSE_KEY = "askflow_admin_sider_collapsed";
const PLACEHOLDER_ROWS = 8;

export function AdminLayout() {
  const nav = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const mobile = screens.lg === false;
  const { features, ready, profile } = useFeatures();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === "1");
  const [drawer, setDrawer] = useState(false);
  const { items, selected, crumb } = useAdminMenu(features, location.pathname);
  useEffect(() => { localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0"); }, [collapsed]);
  useEffect(() => { setDrawer(false); }, [location.pathname]);
  if (!getToken()) return <Navigate to="/login" replace />;
  const menu = ready ? <Menu mode="inline" selectedKeys={[selected]} items={items}
    onClick={({ key }) => nav(String(key))} className="af-pro-menu" /> :
    <div className="af-pro-loading"><Skeleton active paragraph={{ rows: PLACEHOLDER_ROWS }} title={false} /></div>;
  return <Layout className="af-pro-layout">
    <Sidebar {...{ mobile, collapsed, drawer, menu, setCollapsed, setDrawer }} />
    <Layout className="af-pro-main"><AdminHeader {...{ mobile, profile, crumb }} openDrawer={() => setDrawer(true)} />
      <Layout.Content className="af-pro-content"><Outlet /></Layout.Content></Layout>
  </Layout>;
}
