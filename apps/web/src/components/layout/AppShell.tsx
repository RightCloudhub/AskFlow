import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Layout, Space, Typography } from "antd";
import {
  CommentOutlined,
  FormOutlined,
  LogoutOutlined,
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
};

export function AppShell({
  me,
  conversations,
  activeId,
  onSelectConversation,
  onNewChat,
  creating = false,
  children,
  title = "智能客服",
  subtitle = "诚实 RAG · 意图路由 · 可转人工",
}: AppShellProps) {
  const nav = useNavigate();
  const { enabled } = useFeatures();

  function logout() {
    setToken(null);
    nav("/login");
  }

  return (
    <Layout className="af-app-shell">
      <Sider width={280} className="af-app-sider" breakpoint="lg" collapsedWidth={0}>
        <div className="af-app-sider-head">
          <span className="brand-mark sm">AF</span>
          <div>
            <strong>AskFlow</strong>
            <Text type="secondary" className="af-app-sider-tag">
              对话台
            </Text>
          </div>
        </div>
        <Button
          type="primary"
          block
          icon={<CommentOutlined />}
          onClick={onNewChat}
          loading={creating}
          className="af-app-new-chat"
        >
          新建会话
        </Button>
        <ul className="af-conv-list">
          {conversations.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={c.id === activeId ? "active" : ""}
                onClick={() => onSelectConversation(c.id)}
              >
                <span className="title">{c.title}</span>
                <span className="status">{c.status}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="af-app-sider-foot">
          <Text ellipsis className="af-app-user">
            {me?.username ?? "…"}
          </Text>
          <Space size={4} wrap>
            {enabled("ticket") ? (
              <Link to="/tickets">
                <Button type="text" size="small" icon={<FormOutlined />}>
                  工单
                </Button>
              </Link>
            ) : null}
            <Link to="/admin">
              <Button type="text" size="small" icon={<SettingOutlined />}>
                Admin
              </Button>
            </Link>
            <Button
              type="text"
              size="small"
              danger
              icon={<LogoutOutlined />}
              onClick={logout}
            >
              退出
            </Button>
          </Space>
        </div>
      </Sider>
      <Layout>
        <Header className="af-app-header">
          <div>
            <h2>{title}</h2>
            <p>{subtitle}</p>
          </div>
        </Header>
        <Content className="af-app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
