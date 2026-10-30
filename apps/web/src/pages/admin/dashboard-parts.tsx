import { Tabs } from "antd";
import { ArrowRightOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import { HBarChart, StatCard, purposeLabel, type ChartDatum } from "../../components/admin";
import { WorkspacePanel } from "../../components/admin/workspace";
import { useFeatures } from "../../plugins/features";
import type { AnalyticsSummary } from "../../api/types";

const WORKLOAD_CHART_HEIGHT = 192;
const COST_CHART_HEIGHT = 180;

export function metric(summary: AnalyticsSummary, key: keyof AnalyticsSummary) {
  const value = summary[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function finding(summary?: AnalyticsSummary) {
  if (!summary) return "关注待处理服务、回答质量与模型费用。";
  if (summary.sla_breached) return `${summary.sla_breached} 项 SLA 已违约，请优先跟进。`;
  if (summary.handoffs_queued) return `${summary.handoffs_queued} 位客户正在等待人工接管。`;
  if (summary.tickets_open) return `${summary.tickets_open} 个工单需要继续跟进。`;
  const counts = [summary.sla_breached, summary.handoffs_queued, summary.tickets_open];
  if (counts.some((value) => value == null)) return "部分服务统计暂未提供，请查看已加载的记录。";
  return "当前没有排队接管或未结工单。";
}

export function DashboardMetrics({ summary }: { summary: AnalyticsSummary }) {
  return <div className="af-dashboard-metrics">
    <StatCard label="消息总量" value={metric(summary, "messages")} hint="累计客服消息" />
    <StatCard label="未结工单" value={metric(summary, "tickets_open")} hint="等待服务闭环" />
    <StatCard label="等待人工" value={metric(summary, "handoffs_queued")} hint="排队接管会话" />
    <StatCard label="预估模型费用" value={metric(summary, "cost_estimated_usd")} format="usd" hint="累计调用估算 · USD" />
  </div>;
}

const ATTENTION = [
  { key: "sla_breached", label: "SLA 违约", path: "/admin/sla", feature: "sla" },
  { key: "handoff_timeouts", label: "接管超时", path: "/admin/handoffs", feature: "handoff" },
  { key: "thumbs_down", label: "收到差评", path: "/admin/qc", feature: "qc" },
  { key: "gaps_open", label: "知识缺口", path: "/admin/gaps", feature: "knowledge" },
] as const;

export function DashboardAttention({ summary }: { summary: AnalyticsSummary }) {
  const { enabled } = useFeatures();
  return <WorkspacePanel title="需要关注" description="服务异常与知识待办。"><div className="af-dashboard-queue">
    {ATTENTION.map((item) => {
      const value = metric(summary, item.key);
      const content = <><span>{item.label}</span><strong>{value ?? "—"}</strong></>;
      return enabled(item.feature) ? <Link key={item.key} to={item.path}>{content}</Link> :
        <div className="af-dashboard-readonly" key={item.key}>{content}</div>;
    })}
  </div></WorkspacePanel>;
}

const WORKLOAD = [
  { key: "tickets_open", label: "未结工单" },
  { key: "handoffs_queued", label: "人工接管" },
  { key: "gaps_open", label: "知识缺口" },
] as const;

export function DashboardWorkload({ summary }: { summary: AnalyticsSummary }) {
  const data: ChartDatum[] = WORKLOAD.flatMap((item) => {
    const value = metric(summary, item.key);
    return value === null ? [] : [{ ...item, value }];
  });
  return <WorkspacePanel title="服务工作量" description="当前未完成事项，按业务类型分布。">
    <HBarChart data={data} height={WORKLOAD_CHART_HEIGHT} />
    {data.length < WORKLOAD.length && <p className="af-stat-hint">部分工作量统计暂未提供。</p>}
  </WorkspacePanel>;
}

export function DashboardCosts({ summary }: { summary: AnalyticsSummary }) {
  const purposes = (summary.cost?.by_purpose ?? []).map((row, index) => ({
    key: row.purpose ?? `purpose-${index}`, label: purposeLabel(row.purpose ?? "其他"), value: row.estimated_usd,
  }));
  const models = (summary.cost?.by_model ?? []).map((row, index) => ({
    key: row.model ?? `model-${index}`, label: row.model || "未知模型", value: row.estimated_usd,
  }));
  return <WorkspacePanel title="费用分布" description="从累计记录中定位主要费用来源。">
    <Tabs items={[
      { key: "purpose", label: "按用途", children: <HBarChart data={purposes} format="usd" height={COST_CHART_HEIGHT} /> },
      { key: "model", label: "按模型", children: <HBarChart data={models} format="usd" height={COST_CHART_HEIGHT} /> },
    ]} />
  </WorkspacePanel>;
}

const LINKS = [
  { label: "维护回答依据", path: "/admin/documents", feature: "rag" },
  { label: "复核回答质量", path: "/admin/qc", feature: "qc" },
  { label: "查看运行记录", path: "/admin/agent-runs", feature: "agent" },
];

export function DashboardLinks() {
  const { enabled } = useFeatures();
  const links = LINKS.filter((link) => enabled(link.feature));
  if (!links.length) return null;
  return <WorkspacePanel title="持续改善服务"><div className="af-dashboard-links">
    {links.map((link) => <Link key={link.path} to={link.path}><span>{link.label}</span><ArrowRightOutlined /></Link>)}
  </div></WorkspacePanel>;
}
