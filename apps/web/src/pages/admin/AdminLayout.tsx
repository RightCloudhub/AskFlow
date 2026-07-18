import { useMemo, useState } from "react";
import {
  Link,
  Navigate,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  Button,
  ConfigProvider,
  Layout,
  Menu,
  Space,
  Tag,
  Typography,
} from "antd";
import {
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
} from "@ant-design/icons";
import zhCN from "antd/locale/zh_CN";
import type { MenuProps } from "antd";
import { getToken, setToken } from "../../api/client";
import { adminTheme, navIcon } from "../../components/admin";
import { useFeatures } from "../../plugins/features";
import { filterNav, groupNav } from "../../plugins/registry";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

export function AdminLayout() {
  const nav = useNavigate();
  const location = useLocation();
  const { features, ready, profile } = useFeatures();
  const [collapsed, setCollapsed] = useState(false);
  const authed = Boolean(getToken());

  const sections = useMemo(() => groupNav(filterNav(features)), [features]);

  const menuItems: MenuProps["items"] = useMemo(
    () =>
      sections.map(({ group, items }) => ({
        type: "group" as const,
        key: group.id,
        label: group.label,
        children: items.map((item) => ({
          key: item.to,
          icon: navIcon(item.icon),
          label: item.label,
          title: item.hint,
        })),
      })),
    [sections]
  );

  if (!authed) return <Navigate to="/login" replace />;

  const selected =
    location.pathname === "/admin" || location.pathname === "/admin/"
      ? "/admin"
      : location.pathname;

  return (
    <ConfigProvider locale={zhCN} theme={adminTheme}>
      <Layout className="af-pro-layout" style={{ minHeight: "100vh" }}>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          trigger={null}
          width={232}
          className="af-pro-sider"
        >
          <div className={`af-pro-logo ${collapsed ? "collapsed" : ""}`}>
            <span className="af-pro-logo-mark">AF</span>
            {!collapsed ? (
              <div className="af-pro-logo-text">
                <strong>AskFlow</strong>
                <span>企业智能客服</span>
              </div>
            ) : null}
          </div>
          {!ready ? (
            <div className="af-pro-loading">加载功能…</div>
          ) : (
            <Menu
              theme="dark"
              mode="inline"
              selectedKeys={[selected]}
              items={menuItems}
              onClick={({ key }) => nav(String(key))}
              style={{ borderInlineEnd: 0 }}
            />
          )}
        </Sider>
        <Layout>
          <Header className="af-pro-header">
            <Space>
              <Button
                type="text"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed((c) => !c)}
              />
              <Text type="secondary">管理控制台</Text>
              <Tag color="blue">{profile}</Tag>
            </Space>
            <Space>
              <Link to="/">
                <Button type="text" icon={<UserOutlined />}>
                  用户台
                </Button>
              </Link>
              <Button
                type="text"
                danger
                icon={<LogoutOutlined />}
                onClick={() => {
                  setToken(null);
                  nav("/login");
                }}
              >
                退出
              </Button>
            </Space>
          </Header>
          <Content className="af-pro-content">
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
