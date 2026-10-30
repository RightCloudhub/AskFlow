import { Link, Navigate, useLocation } from "react-router-dom";
import { ArrowRightOutlined } from "@ant-design/icons";
import { PageHeader } from "../components/admin";
import { useAdminAccess } from "./use-admin-access";
import { currentWorkspace } from "./access-policy";
import "../styles/admin-workspaces.css";

const SERVICE_PRIORITY = ["handoffs", "tickets", "mall/support"];

function destinationOrder(path: string) {
  const priority = SERVICE_PRIORITY.findIndex((item) => path === `/admin/service/${item}`);
  return priority < 0 ? SERVICE_PRIORITY.length : priority;
}

export function WorkspacePage() {
  const { items, workspaces, user } = useAdminAccess();
  const workspace = currentWorkspace(useLocation().pathname);
  const destinations = workspace ? items.filter((item) => item.to.startsWith(`/admin/${workspace.id}/`))
    .sort((first, second) => destinationOrder(first.to) - destinationOrder(second.to) || first.order - second.order) : [];
  if (!workspace && workspaces.length === 1) return <Navigate to={`/admin/${workspaces[0].id}`} replace />;
  return <div className="af-page"><PageHeader title={workspace?.title ?? "管理工作区"}
    subtitle={workspace?.description ?? `${user?.username ?? "当前账号"}的可用工作区`} />
    {workspace ? <nav className="af-workspace-destinations" aria-label={`${workspace.title}栏目`}>
      {destinations.map((item) => <Link key={item.to} to={item.to}>
        <span><strong>{item.label}</strong><small>{item.hint ?? "查看记录并处理业务"}</small></span><ArrowRightOutlined />
      </Link>)}
    </nav> : <nav className="af-workspace-areas" aria-label="管理工作区">
      {workspaces.map((area) => <Link to={`/admin/${area.id}`} key={area.id}>
        <div><h2>{area.title}</h2><p>{area.description}</p>
          <span>{items.filter((item) => item.to.startsWith(`/admin/${area.id}/`)).map((item) => item.label).join("、")}</span>
        </div><ArrowRightOutlined />
      </Link>)}
    </nav>}
  </div>;
}
