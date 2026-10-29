import { useCallback, useState } from "react";
import { Card, Descriptions, Space, Table, Typography } from "antd";
import { useLocation } from "react-router-dom";
import { mall } from "./client";
import { Feedback, useLoad, type Row } from "./shared";
import { FinanceRecords, Records } from "./AdminRecords";
import { CatalogUpload } from "./CatalogUpload";
import { AdminForms } from "./AdminForms";
import { MALL_ADMIN } from "./admin-registry";
import { useMallPermissions } from "./permissions";

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
  if (module === "dashboard") return <Dashboard />;
  if (!allowed) return <Typography.Text>此操作需要相应商城权限。</Typography.Text>;
  return <Card title={entry?.label ?? "商城管理"}><Space direction="vertical" style={{ width: "100%" }}>
    {module === "wallet" ? <FinanceRecords key={revision} permissions={grants.permissions} /> :
      RESOURCE[module] && <Records key={`${module}:${revision}`} path={RESOURCE[module]} />}
    {module === "account" && <Records key={revision} path="/account/mfa-resets" />}
    {module === "catalog" && <><Records key={revision} path="/catalog/skus" /><CatalogUpload /></>}
    {module === "settings" && grants.permissions.includes("rbac:write") && <Records key={revision} path="/roles" />}
    <AdminForms module={module} permissions={grants.permissions} reload={async () => setRevision((value) => value + 1)} />
  </Space></Card>;
}

function Dashboard() {
  const load = useCallback(() => mall<Row>("/api/v1/admin/mall/dashboard"), []);
  const query = useLoad(load);
  const labels: Record<string, string> = { orders: "订单数", paid_orders: "已支付订单",
    gmv_cents: "支付总额（分）", refunded_orders: "退款订单", currency: "币种",
    wallet_liability_cents: "钱包余额合计（分）", payment_conversion_basis_points: "支付转化率（万分比）",
    refund_rate_basis_points: "退款率（万分比）", risk_events: "风控命中", risk_pending: "待审风控", open_tickets: "待处理工单" };
  return <Card title="商城概览"><Feedback {...query} /><Descriptions items={Object.entries(query.data ?? {}).map(
    ([key, value]) => ({ key, label: labels[key] ?? key, children: String(value) }))} /></Card>;
}

export function InfraPage() {
  const loader = useCallback(() => mall<{ preset: string; ports: Row[] }>("/api/v1/admin/infra"), []);
  const query = useLoad(loader);
  return <Card title={`基础设施 · ${query.data?.preset ?? ""}`}><Feedback {...query} />
    <Table rowKey="port" dataSource={query.data?.ports} pagination={false} columns={[
      { title: "能力", dataIndex: "port" }, { title: "当前实现", dataIndex: "implementation" },
      { title: "多实例安全", dataIndex: "multi_instance_safe", render: (value: boolean) => value ? "是" : "否" },
      { title: "说明", dataIndex: "description" },
    ]} />
  </Card>;
}
