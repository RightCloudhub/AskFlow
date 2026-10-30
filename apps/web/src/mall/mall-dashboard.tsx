import { useCallback } from "react";
import { mall, money } from "./client";
import { useLoad, type Row } from "./shared";
import { MallPage, MallPanel } from "./presentation";
import { MallQuery, QueryRefresh } from "./query-view";
import { HBarChart } from "../components/admin/charts/HBarChart";
import { useFeatures } from "../plugins/features";
import { useMallPermissions } from "./permissions";
import { CommerceDetails, CommerceQueue } from "./dashboard-parts";

const METRICS = [
  { key: "orders", label: "订单总数" }, { key: "paid_orders", label: "已支付订单" },
  { key: "gmv_cents", label: "支付总额" }, { key: "refunded_orders", label: "退款订单" },
];
const ORDER_COUNTS = METRICS.filter((item) => item.key !== "gmv_cents");

export function MallDashboard() {
  const query = useLoad(useCallback(() => mall<Row>("/api/v1/admin/mall/dashboard"), []));
  const { enabled } = useFeatures();
  const { permissions } = useMallPermissions();
  const currency = String(query.data?.currency ?? "CNY");
  const data = query.data ?? {};
  const bars = ORDER_COUNTS.filter((item) => typeof data[item.key] === "number")
    .map((item) => ({ key: item.key, label: item.label, value: Number(data[item.key]) }));
  return <MallPage title="商城运营" description="从订单到资金与服务，查看累计经营情况。" className="af-mall-admin"
    actions={<QueryRefresh query={query} />}><MallQuery query={query}>
    <div className="af-commerce-dashboard"><dl className="af-mall-metrics">{METRICS.map((item) =>
      <div className="af-mall-metric" key={item.key}><dt>{item.label}</dt><dd>{data[item.key] == null ? "—" :
        item.key === "gmv_cents" ? money(Number(data[item.key]), currency) : Number(data[item.key]).toLocaleString("zh-CN")}</dd></div>)}</dl>
      <div className="af-commerce-body"><div className="af-commerce-main">
        <MallPanel title="订单累计数量" description="各项为独立累计指标，退款订单可能同时计入已支付订单。"><HBarChart data={bars} /></MallPanel>
        <CommerceDetails data={data} currency={currency} />
      </div><CommerceQueue data={data} permissions={permissions} enabled={enabled} /></div>
    </div></MallQuery>
  </MallPage>;
}
