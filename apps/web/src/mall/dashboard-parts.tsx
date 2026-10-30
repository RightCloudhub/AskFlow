import { Descriptions } from "antd";
import { ArrowRightOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import { money } from "./client";
import type { Row } from "./shared";
import { MallPanel } from "./presentation";

const BASIS_POINTS_PER_PERCENT = 100;
const PERCENT_DECIMALS = 2;
const DETAIL_GROUPS = [
  { title: "支付与退款", fields: [
    { key: "payment_conversion_basis_points", label: "支付转化率" },
    { key: "refund_rate_basis_points", label: "退款率" }, { key: "currency", label: "币种" },
  ] },
  { title: "资金与风险", fields: [
    { key: "wallet_liability_cents", label: "钱包余额合计" },
    { key: "risk_events", label: "风控命中" }, { key: "risk_pending", label: "待审风控" },
  ] },
];
const QUEUES = [
  { key: "open_tickets", label: "待处理工单", to: "/admin/mall/support", permission: "support:read", plugin: "mall_support" },
  { key: "risk_pending", label: "待审风控", to: "/admin/mall/referral", permission: "risk:review", plugin: "mall_referral" },
];
const DESTINATIONS = [
  { label: "订单记录", to: "/admin/mall/order", permission: "order:read", plugin: "mall_order" },
  { label: "支付核对", to: "/admin/mall/payment", permission: "finance:reconcile", plugin: "mall_payment" },
  { label: "钱包流水", to: "/admin/mall/wallet", permission: "wallet:read", plugin: "mall_wallet" },
  { label: "商品与规格", to: "/admin/mall/catalog", permission: "catalog:write", plugin: "mall_catalog" },
];

function formatMetric(key: string, value: unknown, currency: string) {
  if (value == null) return "—";
  if (key.endsWith("_cents")) return money(Number(value), currency);
  if (key.endsWith("_basis_points")) return `${(Number(value) / BASIS_POINTS_PER_PERCENT).toFixed(PERCENT_DECIMALS)}%`;
  return typeof value === "number" ? value.toLocaleString("zh-CN") : String(value);
}

export function CommerceDetails({ data, currency }: { data: Row; currency: string }) {
  return <div className="af-commerce-details">{DETAIL_GROUPS.map((group) => {
    const fields = group.fields.filter((field) => data[field.key] != null);
    if (!fields.length) return null;
    return <MallPanel key={group.title} title={group.title}><Descriptions column={1}
      items={fields.map((field) => ({ key: field.key, label: field.label,
        children: formatMetric(field.key, data[field.key], currency) }))} /></MallPanel>;
  })}</div>;
}

type QueueProps = { data: Row; permissions: string[]; enabled: (plugin: string) => boolean };

export function CommerceQueue({ data, permissions, enabled }: QueueProps) {
  const allowed = (item: { permission: string; plugin: string }) => permissions.includes(item.permission) && enabled(item.plugin);
  const queues = QUEUES.filter((item) => allowed(item) && data[item.key] != null);
  const destinations = DESTINATIONS.filter(allowed);
  if (!queues.length && !destinations.length) return null;
  return <aside className="af-commerce-aside">
    {queues.length > 0 && <MallPanel title="服务与审核队列"><div className="af-dashboard-queue">
      {queues.map((item) => <Link key={item.key} to={item.to}><span>{item.label}</span>
        <strong>{Number(data[item.key]).toLocaleString("zh-CN")}</strong><ArrowRightOutlined /></Link>)}
    </div></MallPanel>}
    {destinations.length > 0 && <MallPanel title="继续处理"><div className="af-dashboard-links">
      {destinations.map((item) => <Link key={item.to} to={item.to}>{item.label}<ArrowRightOutlined /></Link>)}
    </div></MallPanel>}
  </aside>;
}
