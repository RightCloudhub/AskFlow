import { AppstoreOutlined, DownOutlined, MessageOutlined, ShoppingOutlined } from "@ant-design/icons";
import { Dropdown } from "antd";
import { useNavigate } from "react-router-dom";
import { useFeatures } from "../../plugins/features";

type Workspace = "chat" | "admin" | "shop";
const WORKSPACES = {
  chat: { title: "客服工作台", path: "/", feature: "agent", icon: <MessageOutlined /> },
  shop: { title: "商城与服务", path: "/shop", feature: "mall_core", icon: <ShoppingOutlined /> },
  admin: { title: "管理控制台", path: "/admin", feature: "core", icon: <AppstoreOutlined /> },
};

export function WorkspaceSwitcher({ current, compact = false }: { current: Workspace; compact?: boolean }) {
  const navigate = useNavigate();
  const { enabled } = useFeatures();
  const items = Object.entries(WORKSPACES).filter(([, item]) => enabled(item.feature))
    .map(([key, item]) => ({ key, label: item.title, icon: item.icon }));
  return <Dropdown trigger={["click"]} menu={{ items, selectedKeys: [current],
    onClick: ({ key }) => navigate(WORKSPACES[key as Workspace].path) }}>
    <button className={`af-workspace-switch ${compact ? "compact" : ""}`} type="button" aria-label="切换工作区">
      {WORKSPACES[current].icon}{!compact && <span>{WORKSPACES[current].title}</span>}<DownOutlined />
    </button>
  </Dropdown>;
}
