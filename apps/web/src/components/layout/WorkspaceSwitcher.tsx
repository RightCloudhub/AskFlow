import { AppstoreOutlined, DownOutlined, MessageOutlined, ShoppingOutlined } from "@ant-design/icons";
import { Dropdown } from "antd";
import { useLocation, useNavigate } from "react-router-dom";
import { useFeatures } from "../../plugins/features";
import { useAdminAccess } from "../../admin/use-admin-access";
import { currentWorkspace } from "../../admin/access-policy";

type Workspace = "chat" | "admin" | "shop";
const WORKSPACES = {
  chat: { title: "在线咨询", path: "/", feature: "agent", icon: <MessageOutlined /> },
  shop: { title: "商城与服务", path: "/shop", feature: "mall_core", icon: <ShoppingOutlined /> },
  admin: { title: "管理控制台", path: "/admin", feature: "core", icon: <AppstoreOutlined /> },
};

export function WorkspaceSwitcher({ current, compact = false }: { current: Workspace; compact?: boolean }) {
  const navigate = useNavigate();
  const { enabled } = useFeatures();
  const access = useAdminAccess();
  const requested = currentWorkspace(useLocation().pathname);
  const workspace = access.workspaces.find((area) => area.id === requested?.id);
  const items = Object.entries(WORKSPACES).filter(([key, item]) => key !== "admin" && enabled(item.feature))
    .map(([key, item]) => ({ key, label: item.title, icon: item.icon }));
  items.push(...access.workspaces.map((area) => ({ key: `/admin/${area.id}`, label: area.title, icon: <AppstoreOutlined /> })));
  const selected = current === "admin" ? `/admin/${workspace?.id ?? ""}` : current;
  return <Dropdown trigger={["click"]} menu={{ items, selectedKeys: [selected],
    onClick: ({ key }) => navigate(key.startsWith("/admin/") ? key : WORKSPACES[key as Workspace].path) }}>
    <button className={`af-workspace-switch ${compact ? "compact" : ""}`} type="button" aria-label="切换工作区">
      {WORKSPACES[current].icon}{!compact && <span>{current === "admin" ? workspace?.title ?? "管理工作区" : WORKSPACES[current].title}</span>}<DownOutlined />
    </button>
  </Dropdown>;
}
