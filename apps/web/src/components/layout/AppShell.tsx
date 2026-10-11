import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Avatar,
  Button,
  Drawer,
  Dropdown,
  Empty,
  Grid,
  Layout,
  Tooltip,
  Typography,
} from "antd";
import type { MenuProps } from "antd";
import {
  CustomerServiceOutlined,
  EllipsisOutlined,
  FormOutlined,
  LogoutOutlined,
  MenuOutlined,
  MessageOutlined,
  PlusOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { setToken } from "../../api/client";
import type { Conversation, User } from "../../api/types";
import { useFeatures } from "../../plugins/features";

const { Sider, Content, Header } = Layout;
const { Text } = Typography;

type AppShellProps = {
  me: User | null | undefined;
  conversations: Conversation[];
  activeId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  creating?: boolean;
  children: ReactNode;
  title?: string;
  subtitle?: string;
  /** Extra controls rendered at the right of the header. */
  headerExtra?: ReactNode;
};

const CONV_STATUS: Record<string, { label: string; tone: string }> = {
  active: { label: "进行中", tone: "active" },
  transferred: { label: "已转人工", tone: "handoff" },
  handoff: { label: "人工处理中", tone: "handoff" },
  closed: { label: "已结束", tone: "closed" },
  archived: { label: "已归档", tone: "closed" },
};

function statusOf(status: string) {
  return CONV_STATUS[status] ?? { label: status, tone: "closed" };
}

function ConversationList({
  conversations,
  activeId,
  onSelect,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  if (conversations.length === 0) {
    return (
      <Empty
        className="af-conv-empty"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="还没有会话"
      />
    );
  }
  return (
    <ul className="af-conv-list">
      {conversations.map((c) => {
        const st = statusOf(c.status);
        const Icon =
          st.tone === "handoff" ? CustomerServiceOutlined : MessageOutlined;
        return (
          <li key={c.id}>
            <button
              type="button"
              className={c.id === activeId ? "active" : ""}
              onClick={() => onSelect(c.id)}
              title={c.title}
            >
              <Icon className="af-conv-icon" />
              <span className="af-conv-text">
                <span className="title">{c.title || "未命名会话"}</span>
                <span className={`status status--${st.tone}`}>{st.label}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

type SiderPanelProps = {
  me: User | null | undefined;
  conversations: Conversation[];
  activeId: string | null;
  creating: boolean;
  onNewChat: () => void;
  onSelect: (id: string) => void;
};

function SiderPanel({
  me,
  conversations,
  activeId,
  creating,
  onNewChat,
  onSelect,
}: SiderPanelProps) {
  const nav = useNavigate();
  const { enabled } = useFeatures();

  function logout() {
    setToken(null);
    nav("/login");
  }

  const username = me?.username ?? "…";
  const userMenu: MenuProps = {
    items: [
      ...(enabled("ticket")
        ? [{ key: "tickets", icon: <FormOutlined />, label: "我的工单" }]
        : []),
      { key: "admin", icon: <SettingOutlined />, label: "管理控制台" },
      { type: "divider" as const },
      {
        key: "logout",
        icon: <LogoutOutlined />,
        label: "退出登录",
        danger: true,
      },
    ],
    onClick: ({ key }) => {
      if (key === "tickets") nav("/tickets");
      if (key === "admin") nav("/admin");
      if (key === "logout") logout();
    },
  };

  return (
    <div className="af-app-sider-inner">
      <div className="af-app-sider-head">
        <span className="brand-mark sm">AF</span>
        <div className="af-app-sider-brand">
          <strong>AskFlow</strong>
          <span>智能客服对话台</span>
        </div>
      </div>
      <Button
        type="primary"
        block
        icon={<PlusOutlined />}
        onClick={onNewChat}
        loading={creating}
        className="af-app-new-chat"
      >
        新建会话
      </Button>
      <div className="af-conv-heading">
        <span>最近会话</span>
        <span className="af-conv-count">{conversations.length}</span>
      </div>
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        onSelect={onSelect}
      />
      <div className="af-app-sider-foot">
        <Avatar size={32} className="af-avatar" style={{ fontSize: 13 }}>
          {username.slice(0, 1).toUpperCase()}
        </Avatar>
        <div className="af-app-user">
          <Text strong ellipsis>
            {username}
          </Text>
          <Text type="secondary" ellipsis className="af-app-user-mail">
            {me?.email ?? ""}
          </Text>
        </div>
        <Dropdown menu={userMenu} trigger={["click"]} placement="topRight">
          <Button type="text" icon={<EllipsisOutlined />} aria-label="更多" />
        </Dropdown>
      </div>
    </div>
  );
}

export function AppShell({
  me,
  conversations,
  activeId,
  onSelectConversation,
  onNewChat,
  creating = false,
  children,
  title = "智能客服",
  subtitle = "基于知识库作答，可随时转人工",
  headerExtra,
}: AppShellProps) {
  const { enabled } = useFeatures();
  const screens = Grid.useBreakpoint();
  const isMobile = screens.md === false;
  const [drawerOpen, setDrawerOpen] = useState(false);

  const sider = (
    <SiderPanel
      me={me}
      conversations={conversations}
      activeId={activeId}
      creating={creating}
      onNewChat={() => {
        onNewChat();
        setDrawerOpen(false);
      }}
      onSelect={(id) => {
        onSelectConversation(id);
        setDrawerOpen(false);
      }}
    />
  );

  return (
    <Layout className="af-app-shell">
      {isMobile ? (
        <Drawer
          placement="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          size={280}
          closable={false}
          styles={{ body: { padding: 0 } }}
        >
          {sider}
        </Drawer>
      ) : (
        <Sider width={272} theme="light" className="af-app-sider">
          {sider}
        </Sider>
      )}
      <Layout className="af-app-main">
        <Header className="af-app-header">
          <div className="af-app-header-title">
            {isMobile ? (
              <Button
                type="text"
                icon={<MenuOutlined />}
                onClick={() => setDrawerOpen(true)}
                aria-label="打开会话列表"
              />
            ) : null}
            <div className="af-app-header-text">
              <h2>{title}</h2>
              {subtitle ? <p>{subtitle}</p> : null}
            </div>
          </div>
          <div className="af-app-header-extra">
            {headerExtra}
            {enabled("ticket") && !isMobile ? (
              <Link to="/tickets">
                <Button type="text" icon={<FormOutlined />}>
                  我的工单
                </Button>
              </Link>
            ) : null}
            {isMobile ? (
              <Tooltip title="新建会话">
                <Button
                  type="text"
                  icon={<PlusOutlined />}
                  onClick={onNewChat}
                  loading={creating}
                  aria-label="新建会话"
                />
              </Tooltip>
            ) : null}
          </div>
        </Header>
        <Content className="af-app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
