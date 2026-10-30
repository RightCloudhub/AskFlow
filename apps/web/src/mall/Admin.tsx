import { useCallback, useState } from "react";
import { Table } from "antd";
import { useLocation } from "react-router-dom";
import { mall } from "./client";
import { Feedback, useLoad, type Row } from "./shared";
import { FinanceRecords, Records } from "./AdminRecords";
import { CatalogUpload } from "./CatalogUpload";
import { AdminForms, hasAdminOperations } from "./AdminForms";
import { MALL_ADMIN } from "./admin-registry";
import { useMallPermissions } from "./permissions";
import { MallDashboard } from "./mall-dashboard";
import { MallEmpty, MallPage, MallPanel } from "./presentation";
import "../styles/mall.css";

const RESOURCE: Record<string, string> = {
  catalog: "/catalog", order: "/order", payment: "/payment", wallet: "/wallet/accounts",
  referral: "/referral", notify: "/notify/deliveries", support: "/support", settings: "/settings",
  account: "/account", inventory: "/inventory",
};

export function MallAdmin() {
  const [revision, setRevision] = useState(0);
  const module = useLocation().pathname.split("/").slice(-1)[0] ?? "settings";
  const grants = useMallPermissions();
  const entry = MALL_ADMIN.find((item) => item.module === module);
  const allowed = grants.permissions.includes(entry?.permission ?? "");
  if (module === "dashboard") return <MallDashboard />;
  if (!allowed) return <MallPage title={entry?.label ?? "商城管理"}><Feedback {...grants} />
    {!grants.loading && <MallEmpty title="此操作需要相应商城权限。" />}</MallPage>;
  return <MallPage title={entry?.label ?? "商城管理"} description="查看业务记录，按权限执行管理操作。" className="af-mall-admin">
    <div className="af-mall-admin-stack"><MallPanel title="业务记录">
    {module === "wallet" ? <FinanceRecords key={revision} permissions={grants.permissions} /> :
      RESOURCE[module] && <Records key={`${module}:${revision}`} path={RESOURCE[module]} />}
    </MallPanel>
    {module === "account" && <MallPanel title="二步验证重置申请"><Records key={revision} path="/account/mfa-resets" /></MallPanel>}
    {module === "catalog" && <><MallPanel title="商品规格"><Records key={revision} path="/catalog/skus" /></MallPanel>
      <MallPanel title="上传商品图片"><CatalogUpload /></MallPanel></>}
    {module === "settings" && grants.permissions.includes("rbac:write") && <MallPanel title="角色记录"><Records key={revision} path="/roles" /></MallPanel>}
    {hasAdminOperations(module, grants.permissions) && <MallPanel title="管理操作">
    <AdminForms module={module} permissions={grants.permissions} reload={async () => setRevision((value) => value + 1)} />
    </MallPanel>}</div></MallPage>;
}

export function InfraPage() {
  const loader = useCallback(() => mall<{ preset: string; ports: Row[] }>("/api/v1/admin/infra"), []);
  const query = useLoad(loader);
  return <MallPage title="基础设施" description={query.data?.preset ? `当前部署方案：${query.data.preset}` : "查看能力实现与多实例支持情况。"} className="af-mall-admin">
    <Feedback {...query} /><MallPanel title="能力实现">
    <Table rowKey="port" dataSource={query.data?.ports} pagination={false} columns={[
      { title: "能力", dataIndex: "port" }, { title: "当前实现", dataIndex: "implementation" },
      { title: "多实例安全", dataIndex: "multi_instance_safe", render: (value: boolean) => value ? "是" : "否" },
      { title: "说明", dataIndex: "description" },
    ]} scroll={{ x: true }} />
    </MallPanel></MallPage>;
}
