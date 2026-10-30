import type { ReactNode } from "react";
import { Avatar, Breadcrumb, Button, Drawer, Dropdown, Layout, Typography } from "antd";
import { DownOutlined, LogoutOutlined, MenuFoldOutlined, MenuOutlined, MenuUnfoldOutlined, MessageOutlined } from "@ant-design/icons";
import { Link, useNavigate } from "react-router-dom";
import { setToken } from "../../api/client";
import { useMe } from "../../hooks/use-auth";
import { useFeatures } from "../../plugins/features";
import { logoutMallSession } from "../../mall/session";
import { BrandMark } from "../../components/layout/BrandMark";
import { WorkspaceSwitcher } from "../../components/layout/WorkspaceSwitcher";
import { DESIGN } from "../../design/tokens";

const SIDEBAR_COLLAPSED = 72;
const DRAWER_WIDTH = 288;
const AVATAR_SIZE = 32;

function Brand({ collapsed }: { collapsed: boolean }) {
  return <Link to="/admin" aria-label="AskFlow 管理控制台" className={`af-pro-logo ${collapsed ? "collapsed" : ""}`}>
    <BrandMark />{!collapsed && <span className="af-pro-logo-text"><strong>AskFlow</strong><span>让服务有迹可循</span></span>}
  </Link>;
}

export function UserChip({ compact }: { compact: boolean }) {
  const navigate = useNavigate();
  const me = useMe();
  const { enabled } = useFeatures();
  const username = me.data?.username ?? "账号";
  async function logout() {
    if (enabled("mall_account")) await logoutMallSession();
    else setToken(null);
    navigate("/login");
  }
  const menu = { items: [
    ...(enabled("agent") ? [{ key: "chat", icon: <MessageOutlined />, label: "前往客服工作台" }] : []),
    { key: "logout", icon: <LogoutOutlined />, label: "退出登录", danger: true }],
    onClick: ({ key }: { key: string }) => { if (key === "chat") navigate("/"); else void logout(); } };
  return <Dropdown menu={menu} trigger={["click"]} placement="bottomRight">
    <button type="button" className="af-user-chip" aria-label={`${username}的账号菜单`}>
      <Avatar size={AVATAR_SIZE} className="af-avatar">{username.slice(0, 1).toUpperCase()}</Avatar>
      {!compact && <Typography.Text className="af-user-chip-name">{username}</Typography.Text>}<DownOutlined />
    </button>
  </Dropdown>;
}

type SidebarProps = { mobile: boolean; collapsed: boolean; drawer: boolean; menu: ReactNode;
  setCollapsed: (value: boolean) => void; setDrawer: (value: boolean) => void };

export function Sidebar(props: SidebarProps) {
  const content = <><Brand collapsed={!props.mobile && props.collapsed} />
    <div className="af-pro-workspace"><WorkspaceSwitcher current="admin" compact={!props.mobile && props.collapsed} /></div>
    <div className="af-pro-menu-wrap">{props.menu}</div></>;
  if (props.mobile) return <Drawer title="管理导航" placement="left" open={props.drawer} size={DRAWER_WIDTH}
    onClose={() => props.setDrawer(false)} styles={{ body: { padding: 0 } }} className="af-pro-drawer">
    {content}<div className="af-pro-sider-account"><UserChip compact={false} /></div></Drawer>;
  return <Layout.Sider collapsed={props.collapsed} trigger={null} width={DESIGN.sidebar}
    collapsedWidth={SIDEBAR_COLLAPSED} theme="light" className="af-pro-sider">
    {content}<div className="af-pro-sider-foot"><UserChip compact={props.collapsed} />
      <Button type="text" icon={props.collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        aria-label={props.collapsed ? "展开侧栏" : "收起侧栏"} onClick={() => props.setCollapsed(!props.collapsed)} />
    </div>
  </Layout.Sider>;
}

export function AdminHeader(props: { mobile: boolean; profile: string; search: ReactNode;
  crumb: { group: string; page: string } | null; openDrawer: () => void }) {
  const items = [{ title: <Link to="/admin">控制台</Link> }, ...(props.crumb ? [
    { title: props.crumb.group }, { title: props.crumb.page }] : [])];
  return <Layout.Header className="af-pro-header"><div className="af-pro-header-left">
    {props.mobile && <Button type="text" icon={<MenuOutlined />} onClick={props.openDrawer} aria-label="打开导航" />}
    {props.mobile && <span className="af-pro-mobile-brand">AskFlow</span>}<Breadcrumb items={items} />
    </div><div className="af-pro-header-right">{props.search}
      {!props.mobile && <span className="af-deployment-scope">{props.profile === "unknown" ? "当前工作区" : props.profile}</span>}
      {props.mobile && <UserChip compact />}
    </div></Layout.Header>;
}
