import type { ReactNode } from "react";
import { Avatar, Breadcrumb, Button, Drawer, Dropdown, Layout, Tag, Typography } from "antd";
import { DownOutlined, LogoutOutlined, MenuFoldOutlined, MenuOutlined, MenuUnfoldOutlined, MessageOutlined } from "@ant-design/icons";
import { Link, useNavigate } from "react-router-dom";
import { setToken } from "../../api/client";
import { useMe } from "../../hooks/use-auth";
import { useFeatures } from "../../plugins/features";
import { logoutMallSession } from "../../mall/session";

const SIDEBAR_WIDTH = 236;
const SIDEBAR_COLLAPSED = 68;
const DRAWER_WIDTH = 260;
const AVATAR_SIZE = 28;

function Brand({ collapsed }: { collapsed: boolean }) {
  return <Link to="/admin" className={`af-pro-logo ${collapsed ? "collapsed" : ""}`}>
    <span className="af-pro-logo-mark">AF</span>
    {!collapsed && <span className="af-pro-logo-text"><strong>AskFlow</strong><span>管理控制台</span></span>}
  </Link>;
}

function UserChip({ compact }: { compact: boolean }) {
  const nav = useNavigate();
  const me = useMe();
  const { enabled } = useFeatures();
  const username = me.data?.username ?? "…";
  const logout = async () => {
    if (enabled("mall_account")) await logoutMallSession();
    else setToken(null);
    nav("/login");
  };
  const menu = { items: [{ key: "chat", icon: <MessageOutlined />, label: "前往对话台" },
    { key: "logout", icon: <LogoutOutlined />, label: "退出登录", danger: true }],
    onClick: ({ key }: { key: string }) => { if (key === "chat") nav("/"); else void logout(); } };
  return <Dropdown menu={menu} trigger={["click"]} placement="bottomRight">
    <button type="button" className="af-user-chip"><Avatar size={AVATAR_SIZE} className="af-avatar">
      {username.slice(0, 1).toUpperCase()}</Avatar>
      {!compact && <Typography.Text className="af-user-chip-name">{username}</Typography.Text>}
      <DownOutlined className="af-user-chip-caret" /></button>
  </Dropdown>;
}

type SidebarProps = { mobile: boolean; collapsed: boolean; drawer: boolean; menu: ReactNode;
  setCollapsed: (value: boolean) => void; setDrawer: (value: boolean) => void };

export function Sidebar(props: SidebarProps) {
  if (props.mobile) return <Drawer placement="left" open={props.drawer} size={DRAWER_WIDTH}
    onClose={() => props.setDrawer(false)} closable={false} styles={{ body: { padding: 0 } }} className="af-pro-drawer">
    <Brand collapsed={false} />{props.menu}</Drawer>;
  return <Layout.Sider collapsed={props.collapsed} trigger={null} width={SIDEBAR_WIDTH}
    collapsedWidth={SIDEBAR_COLLAPSED} theme="light" className="af-pro-sider">
    <Brand collapsed={props.collapsed} /><div className="af-pro-menu-wrap">{props.menu}</div>
    <div className="af-pro-sider-foot"><Button type="text" block
      icon={props.collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
      onClick={() => props.setCollapsed(!props.collapsed)}>{props.collapsed ? null : "收起侧栏"}</Button></div>
  </Layout.Sider>;
}

export function AdminHeader(props: { mobile: boolean; profile: string;
  crumb: { group: string; page: string } | null; openDrawer: () => void }) {
  const items = [{ title: "控制台" }, ...(props.crumb ? [
    { title: props.crumb.group }, { title: props.crumb.page }] : [])];
  return <Layout.Header className="af-pro-header"><div className="af-pro-header-left">
    {props.mobile && <Button type="text" icon={<MenuOutlined />} onClick={props.openDrawer} aria-label="打开导航" />}
    <Breadcrumb items={items} /></div><div className="af-pro-header-right">
    {!props.mobile && <><Tag variant="filled" color="processing" className="af-profile-tag">{props.profile}</Tag>
      <Link to="/"><Button type="text" icon={<MessageOutlined />}>对话台</Button></Link></>}
    <UserChip compact={props.mobile} /></div></Layout.Header>;
}
