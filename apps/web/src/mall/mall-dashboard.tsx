import { useCallback } from "react";
import { Button, Descriptions } from "antd";
import { mall, money } from "./client";
import { Feedback, useLoad, type Row } from "./shared";
import { MallPage, MallPanel } from "./presentation";

const BASIS_POINTS_PER_PERCENT = 100;
const COUNT_FORMAT = new Intl.NumberFormat("zh-CN");
const METRICS = [
  { key: "orders", label: "订单总数" }, { key: "paid_orders", label: "已支付订单" },
  { key: "gmv_cents", label: "支付总额" }, { key: "open_tickets", label: "待处理工单" },
];
const LABELS: Record<string, string> = {
  refunded_orders: "退款订单", currency: "币种", wallet_liability_cents: "钱包余额合计",
  payment_conversion_basis_points: "支付转化率", refund_rate_basis_points: "退款率",
  risk_events: "风控命中", risk_pending: "待审风控",
};

function formatMetric(key: string, value: unknown, currency: string) {
  if (value == null) return "—";
  if (key.endsWith("_cents")) return money(Number(value), currency);
  if (key.endsWith("_basis_points")) return `${(Number(value) / BASIS_POINTS_PER_PERCENT).toFixed(2)}%`;
  return typeof value === "number" ? COUNT_FORMAT.format(value) : String(value);
}

export function MallDashboard() {
  const load = useCallback(() => mall<Row>("/api/v1/admin/mall/dashboard"), []);
  const query = useLoad(load);
  const currency = String(query.data?.currency ?? "CNY");
  const details = Object.entries(query.data ?? {}).filter(([key]) => !METRICS.some((item) => item.key === key));
  return <MallPage title="商城概览" description="查看订单、支付、钱包与客服的运营情况。" className="af-mall-admin"
    actions={<Button loading={query.loading} onClick={() => void query.reload()}>刷新数据</Button>}>
    <Feedback {...query} />
    <dl className="af-mall-metrics">{METRICS.map((item) => <div className="af-mall-metric" key={item.key}>
      <dt>{item.label}</dt><dd>{formatMetric(item.key, query.data?.[item.key], currency)}</dd>
    </div>)}</dl>
    <MallPanel title="经营与服务明细"><Descriptions className="af-mall-description-list" column={{ xs: 1, sm: 2, lg: 3 }}
      items={details.map(([key, value]) => ({ key, label: LABELS[key] ?? key, children: formatMetric(key, value, currency) }))} />
    </MallPanel>
  </MallPage>;
}
