import { Avatar, Button, Dropdown, Empty, Typography, type MenuProps } from "antd";
import { useNavigate } from "react-router-dom";
import { CustomerServiceOutlined, EllipsisOutlined, FormOutlined, LogoutOutlined, MessageOutlined,
  PlusOutlined, SettingOutlined, ShoppingOutlined } from "@ant-design/icons";
import { setToken } from "../../api/client";
import type { Conversation, User } from "../../api/types";
import { useFeatures } from "../../plugins/features";
import { logoutMallSession } from "../../mall/session";

const AVATAR_SIZE = 32;
const AVATAR_FONT_SIZE = 13;
const STATUS: Record<string, { label: string; tone: string }> = {
  active: { label: "进行中", tone: "active" }, transferred: { label: "已转人工", tone: "handoff" },
  handoff: { label: "人工处理中", tone: "handoff" }, closed: { label: "已结束", tone: "closed" },
  archived: { label: "已归档", tone: "closed" },
};
type SidebarProps = { me: User | null | undefined; conversations: Conversation[]; activeId: string | null;
  creating: boolean; onNewChat: () => void; onSelect: (id: string) => void };

function ConversationList(props: Pick<SidebarProps, "conversations" | "activeId" | "onSelect">) {
  if (!props.conversations.length) return <Empty className="af-conv-empty"
    image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有会话" />;
  return <ul className="af-conv-list">{props.conversations.map((conversation) => {
    const status = STATUS[conversation.status] ?? { label: conversation.status, tone: "closed" };
    const Icon = status.tone === "handoff" ? CustomerServiceOutlined : MessageOutlined;
    return <li key={conversation.id}><button type="button" title={conversation.title}
      className={conversation.id === props.activeId ? "active" : ""} onClick={() => props.onSelect(conversation.id)}>
      <Icon className="af-conv-icon" /><span className="af-conv-text">
        <span className="title">{conversation.title || "未命名会话"}</span>
        <span className={`status status--${status.tone}`}>{status.label}</span></span></button></li>;
  })}</ul>;
}

function UserFooter({ me }: { me: User | null | undefined }) {
  const navigate = useNavigate();
  const { enabled } = useFeatures();
  const username = me?.username ?? "…";
  async function logout() {
    if (enabled("mall_account")) await logoutMallSession();
    else setToken(null);
    navigate("/login");
  }
  const destinations: Record<string, string> = { tickets: "/tickets", admin: "/admin", shop: "/shop" };
  const menu: MenuProps = {
    items: [
      ...(enabled("ticket") ? [{ key: "tickets", icon: <FormOutlined />, label: "我的工单" }] : []),
      ...(enabled("mall_core") ? [{ key: "shop", icon: <ShoppingOutlined />, label: "商城" }] : []),
      { key: "admin", icon: <SettingOutlined />, label: "管理控制台" }, { type: "divider" },
      { key: "logout", icon: <LogoutOutlined />, label: "退出登录", danger: true },
    ],
    onClick: ({ key }) => { if (key === "logout") void logout(); else navigate(destinations[key]); },
  };
  return <div className="af-app-sider-foot"><Avatar size={AVATAR_SIZE} className="af-avatar" style={{ fontSize: AVATAR_FONT_SIZE }}>
    {username.slice(0, 1).toUpperCase()}</Avatar><div className="af-app-user">
      <Typography.Text strong ellipsis>{username}</Typography.Text>
      <Typography.Text type="secondary" ellipsis className="af-app-user-mail">{me?.email ?? ""}</Typography.Text></div>
    <Dropdown menu={menu} trigger={["click"]} placement="topRight">
      <Button type="text" icon={<EllipsisOutlined />} aria-label="更多" /></Dropdown></div>;
}

export function SiderPanel(props: SidebarProps) {
  return <div className="af-app-sider-inner"><div className="af-app-sider-head">
    <span className="brand-mark sm">AF</span><div className="af-app-sider-brand">
      <strong>AskFlow</strong><span>智能客服对话台</span></div></div>
    <Button type="primary" block icon={<PlusOutlined />} onClick={props.onNewChat}
      loading={props.creating} className="af-app-new-chat">新建会话</Button>
    <div className="af-conv-heading"><span>最近会话</span><span className="af-conv-count">{props.conversations.length}</span></div>
    <ConversationList {...props} /><UserFooter me={props.me} /></div>;
}
