import { useState, type ReactNode } from "react";
import { Button, Drawer, Grid, Layout, Tooltip } from "antd";
import { MenuOutlined, PlusOutlined } from "@ant-design/icons";
import type { Conversation, User } from "../../api/types";
import { SiderPanel } from "./shell-sidebar";
import { DESIGN } from "../../design/tokens";

const DRAWER_WIDTH = 288;
type AppShellProps = {
  me: User | null | undefined; conversations: Conversation[]; activeId: string | null;
  onSelectConversation: (id: string) => void; onNewChat: () => void; creating?: boolean;
  children: ReactNode; title?: string; subtitle?: string; headerExtra?: ReactNode;
};

function ChatHeader(props: AppShellProps & { mobile: boolean; openDrawer: () => void }) {
  return <Layout.Header className="af-app-header"><div className="af-app-header-title">
    {props.mobile && <Button type="text" icon={<MenuOutlined />} onClick={props.openDrawer} aria-label="打开会话列表" />}
    <div className="af-app-header-text"><h1 title={props.title}>{props.title ?? "客服工作台"}</h1>
      {props.subtitle && <p>{props.subtitle}</p>}</div></div>
    <div className="af-app-header-extra">{props.headerExtra}
      {props.mobile && <Tooltip title="新建会话"><Button type="text" icon={<PlusOutlined />}
        onClick={props.onNewChat} loading={props.creating} aria-label="新建会话" /></Tooltip>}
    </div></Layout.Header>;
}

export function AppShell(props: AppShellProps) {
  const screens = Grid.useBreakpoint();
  const mobile = screens.lg === false;
  const [drawer, setDrawer] = useState(false);
  const sidebar = <SiderPanel me={props.me} conversations={props.conversations} activeId={props.activeId}
    creating={props.creating ?? false} onNewChat={() => { props.onNewChat(); setDrawer(false); }}
    onSelect={(id) => { props.onSelectConversation(id); setDrawer(false); }} />;
  return <Layout className="af-app-shell">
    {mobile ? <Drawer title="客服工作台" placement="left" open={drawer} onClose={() => setDrawer(false)} size={DRAWER_WIDTH}
      styles={{ body: { padding: 0 } }}>{sidebar}</Drawer> :
      <Layout.Sider width={DESIGN.sidebar} theme="light" className="af-app-sider">{sidebar}</Layout.Sider>}
    <Layout className="af-app-main"><ChatHeader {...props} mobile={mobile} openDrawer={() => setDrawer(true)} />
      <Layout.Content className="af-app-content">{props.children}</Layout.Content></Layout>
  </Layout>;
}
