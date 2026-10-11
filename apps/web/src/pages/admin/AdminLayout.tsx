import { useEffect, useMemo, useState } from "react";
import {
  Link,
  Navigate,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  Avatar,
  Breadcrumb,
  Button,
  Drawer,
  Dropdown,
  Grid,
  Layout,
  Menu,
  Skeleton,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  DownOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuOutlined,
  MenuUnfoldOutlined,
  MessageOutlined,
} from "@ant-design/icons";
import type { MenuProps } from "antd";
import { getToken, setToken } from "../../api/client";
import { navIcon } from "../../components/admin";
import { useMe } from "../../hooks/use-auth";
import { useFeatures } from "../../plugins/features";
import { filterNav, groupNav } from "../../plugins/registry";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;
const COLLAPSE_KEY = "askflow_admin_sider_collapsed";

function Brand({ collapsed }: { collapsed: boolean }) {
  return (
    <Link to="/admin" className={`af-pro-logo ${collapsed ? "collapsed" : ""}`}>
      <span className="af-pro-logo-mark">AF</span>
      {!collapsed ? (
        <span className="af-pro-logo-text">
          <strong>AskFlow</strong>
          <span>管理控制台</span>
        </span>
      ) : null}
    </Link>
  );
}

function UserChip({ compact }: { compact: boolean }) {
  const nav = useNavigate();
  const meQ = useMe();
  const username = meQ.data?.username ?? "…";
  const userMenu: MenuProps = {
    items: [
      {
        key: "who",
        disabled: true,
        label: (
          <div className="af-user-menu-head">
            <strong>{username}</strong>
            <span>{meQ.data?.email ?? ""}</span>
          </div>
        ),
      },
      { type: "divider" },
      { key: "chat", icon: <MessageOutlined />, label: "前往对话台" },
      {
        key: "logout",
        icon: <LogoutOutlined />,
        label: "退出登录",
        danger: true,
      },
    ],
    onClick: ({ key }) => {
      if (key === "chat") nav("/");
      if (key === "logout") {
        setToken(null);
        nav("/login");
      }
    },
  };
  return (
    <Dropdown menu={userMenu} trigger={["click"]} placement="bottomRight">
      <button type="button" className="af-user-chip">
        <Avatar size={28} className="af-avatar" style={{ fontSize: 13 }}>
          {username.slice(0, 1).toUpperCase()}
        </Avatar>
        {!compact ? (
          <Text className="af-user-chip-name">{username}</Text>
        ) : null}
        <DownOutlined className="af-user-chip-caret" />
      </button>
    </Dropdown>
  );
}

function useAdminMenu(features: Set<string>, pathname: string) {
  const sections = useMemo(() => groupNav(filterNav(features)), [features]);
  const items: MenuProps["items"] = useMemo(
    () =>
      sections.map(({ group, items: navItems }) => ({
        type: "group" as const,
        key: group.id,
        label: group.label,
        children: navItems.map((item) => ({
          key: item.to,
          icon: navIcon(item.icon),
          label: item.label,
          title: item.hint,
        })),
      })),
    [sections],
  );
  const selected =
    pathname === "/admin" || pathname === "/admin/"
      ? "/admin"
      : pathname.replace(/\/$/, "");
  const crumb = useMemo(() => {
    for (const { group, items: navItems } of sections) {
      const hit = navItems.find((i) => i.to === selected);
      if (hit) return { group: group.label, page: hit.label };
    }
    return null;
  }, [sections, selected]);
  return { items, selected, crumb };
}

export function AdminLayout() {
  const nav = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const isMobile = screens.md === false;
  const { features, ready, profile } = useFeatures();
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(COLLAPSE_KEY) === "1",
  );
  const [drawerOpen, setDrawerOpen] = useState(false);
  const authed = Boolean(getToken());

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  const {
    items: menuItems,
    selected,
    crumb,
  } = useAdminMenu(features, location.pathname);

  if (!authed) return <Navigate to="/login" replace />;

  const menu = !ready ? (
    <div className="af-pro-loading">
      <Skeleton active paragraph={{ rows: 8 }} title={false} />
    </div>
  ) : (
    <Menu
      mode="inline"
      selectedKeys={[selected]}
      items={menuItems}
      onClick={({ key }) => nav(String(key))}
      className="af-pro-menu"
    />
  );

  return (
    <Layout className="af-pro-layout">
      {isMobile ? (
        <Drawer
          placement="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          size={260}
          closable={false}
          styles={{ body: { padding: 0 } }}
          className="af-pro-drawer"
        >
          <Brand collapsed={false} />
          {menu}
        </Drawer>
      ) : (
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          trigger={null}
          width={236}
          collapsedWidth={68}
          theme="light"
          className="af-pro-sider"
        >
          <Brand collapsed={collapsed} />
          <div className="af-pro-menu-wrap">{menu}</div>
          <div className="af-pro-sider-foot">
            <Tooltip
              title={collapsed ? "展开侧栏" : "收起侧栏"}
              placement="right"
            >
              <Button
                type="text"
                block
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed((c) => !c)}
              >
                {collapsed ? null : "收起侧栏"}
              </Button>
            </Tooltip>
          </div>
        </Sider>
      )}
      <Layout className="af-pro-main">
        <Header className="af-pro-header">
          <div className="af-pro-header-left">
            {isMobile ? (
              <Button
                type="text"
                icon={<MenuOutlined />}
                onClick={() => setDrawerOpen(true)}
                aria-label="打开导航"
              />
            ) : null}
            <Breadcrumb
              items={[
                { title: "控制台" },
                ...(crumb
                  ? [
                      { title: crumb.group },
                      { title: <strong>{crumb.page}</strong> },
                    ]
                  : []),
              ]}
            />
          </div>
          <div className="af-pro-header-right">
            {!isMobile ? (
              <Tooltip title="当前运行 Profile">
                <Tag
                  variant="filled"
                  color="processing"
                  className="af-profile-tag"
                >
                  {profile}
                </Tag>
              </Tooltip>
            ) : null}
            {!isMobile ? (
              <Link to="/">
                <Button type="text" icon={<MessageOutlined />}>
                  对话台
                </Button>
              </Link>
            ) : null}
            <UserChip compact={isMobile} />
          </div>
        </Header>
        <Content className="af-pro-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
