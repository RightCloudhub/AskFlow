import { Card } from "antd";
import { Link } from "react-router-dom";
import { BarChart, HBarChart, StatCard, purposeLabel, type ChartDatum } from "../../components/admin";
import { useFeatures } from "../../plugins/features";
import type { AnalyticsSummary } from "../../api/types";
const WORKLOAD_CHART_HEIGHT = 220;
const COST_CHART_HEIGHT = 180;

export function metric(summary: AnalyticsSummary, key: keyof AnalyticsSummary) {
  const value = summary[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function finding(summary?: AnalyticsSummary) {
  if (!summary) return "查看客服工作量、待处理事项与模型费用。";
  if (summary.sla_breached) return `${summary.sla_breached} 项 SLA 已违约，请优先跟进工单。`;
  if (summary.handoffs_queued) return `${summary.handoffs_queued} 个会话正在等待人工接管。`;
  if (summary.tickets_open) return `${summary.tickets_open} 个工单待跟进。`;
  const counts = [summary.sla_breached, summary.handoffs_queued, summary.tickets_open];
  if (counts.some((value) => value == null)) return "部分客服任务统计暂未提供，请查看已加载的数据。";
  return "当前没有排队接管或未结工单。";
}

export function DashboardMetrics({ summary }: { summary: AnalyticsSummary }) {
  return <div className="af-dashboard-metrics">
    <StatCard label="消息总量" value={metric(summary, "messages")} />
    <StatCard label="未结工单" value={metric(summary, "tickets_open")} />
    <StatCard label="排队接管" value={metric(summary, "handoffs_queued")} />
    <StatCard label="预估模型费用" value={metric(summary, "cost_estimated_usd")} format="usd" />
  </div>;
}

const ATTENTION = [
  { key: "sla_breached", label: "SLA 违约", path: "/admin/sla", feature: "sla" },
  { key: "handoff_timeouts", label: "接管超时", path: "/admin/handoffs", feature: "handoff" },
  { key: "thumbs_down", label: "收到差评", path: "/admin/qc", feature: "qc" },
  { key: "gaps_open", label: "开放知识缺口", path: "/admin/gaps", feature: "knowledge" },
] as const;

export function DashboardAttention({ summary }: { summary: AnalyticsSummary }) {
  const { enabled } = useFeatures();
  return <Card title="待关注事项"><div className="af-dashboard-queue">{ATTENTION.map((item) => {
    const value = metric(summary, item.key);
    const content = <><span>{item.label}</span><strong>{value ?? "—"}</strong></>;
    return enabled(item.feature) ? <Link key={item.key} to={item.path}>{content}</Link> :
      <div className="af-dashboard-readonly" key={item.key}>{content}</div>;
  })}</div></Card>;
}

const WORKLOAD = [
  { key: "tickets_open", label: "未结工单" },
  { key: "handoffs_queued", label: "排队接管" },
  { key: "gaps_open", label: "知识缺口" },
] as const;

export function DashboardWorkload({ summary }: { summary: AnalyticsSummary }) {
  const data: ChartDatum[] = WORKLOAD.flatMap((item) => {
    const value = metric(summary, item.key);
    return value === null ? [] : [{ ...item, value }];
  });
  return <Card title="当前待处理工作量"><BarChart data={data} height={WORKLOAD_CHART_HEIGHT} unit=" 项" />
    {data.length < WORKLOAD.length && <p className="af-stat-hint">部分工作量统计暂未提供。</p>}
  </Card>;
}

export function DashboardCosts({ summary }: { summary: AnalyticsSummary }) {
  const purposes = (summary.cost?.by_purpose ?? []).map((row, index) => ({
    key: row.purpose ?? `purpose-${index}`, label: purposeLabel(row.purpose ?? "其他"), value: row.estimated_usd,
  }));
  const models = (summary.cost?.by_model ?? []).map((row, index) => ({
    key: row.model ?? `model-${index}`, label: row.model || "未知模型", value: row.estimated_usd,
  }));
  return <div className="af-dashboard-grid">
    <Card title="模型费用 · 按用途"><HBarChart data={purposes} format="usd" height={COST_CHART_HEIGHT} /></Card>
    <Card title="模型费用 · 按模型"><HBarChart data={models} format="usd" height={COST_CHART_HEIGHT} /></Card>
  </div>;
}
