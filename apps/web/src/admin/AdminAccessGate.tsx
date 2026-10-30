import type { ReactNode } from "react";
import { Alert, Button, Spin } from "antd";
import { Link, useLocation } from "react-router-dom";
import { useAdminAccess } from "./use-admin-access";

export function AdminAccessGate({ children }: { children: ReactNode }) {
  const access = useAdminAccess();
  const pathname = useLocation().pathname.replace(/\/$/, "");
  if (access.loading) return <div className="af-query-state"><Spin description="正在确认访问权限…" /></div>;
  if (access.error) return <div className="af-page"><h1>访问权限暂不可用</h1>
    <Alert type="error" title="无法读取当前账号的权限" description="重试后继续进入工作区。"
      action={<Button onClick={() => void access.reload()}>重新读取</Button>} /></div>;
  const allowed = pathname === "/admin" || access.items.some((item) => item.to === pathname)
    || access.workspaces.some((workspace) => pathname === `/admin/${workspace.id}`);
  if (!allowed || !access.items.length) return <div className="af-page"><h1>暂无访问权限</h1>
    <p>当前账号没有此栏目的访问权限。</p>
    {access.items.length > 0 && <Link to="/admin">返回可用工作区</Link>}
    <Link to="/">返回首页</Link></div>;
  return <>{children}</>;
}
