import { PageHeader, StatCard, HBarChart, formatNumber, formatUsd, purposeLabel } from "../../components/admin";
import type { ChartDatum } from "../../components/admin";
import { Tabs } from "antd";
import type { ColumnsType } from "antd/es/table";
import { DataTable, QueryFeedback, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useCostSummary } from "../../hooks/use-governance";
import type { CostBucket } from "../../api/types";

type CostKey = "estimated_usd" | "calls" | "prompt_tokens" | "completion_tokens";
function sum(rows: CostBucket[], key: CostKey) {
  if (rows.some((row) => row[key] == null || !Number.isFinite(row[key]))) return null;
  return rows.reduce((total, row) => total + Number(row[key]), 0);
}
function chart(rows: CostBucket[], field: "purpose" | "model"): ChartDatum[] {
  return rows.map((row, index) => ({ key: String(row[field] ?? index),
    label: field === "purpose" ? purposeLabel(row.purpose ?? "其他") : row.model || "未知模型", value: row.estimated_usd }));
}
function CostMetrics({ rows, loaded }: { rows: CostBucket[]; loaded: boolean }) {
  return <div className="af-dashboard-metrics">
    <StatCard label="预估总费用" value={loaded ? sum(rows, "estimated_usd") : null} format="usd" hint="累计调用估算 · USD" />
    <StatCard label="模型调用次数" value={loaded ? sum(rows, "calls") : null} />
    <StatCard label="输入 Token" value={loaded ? sum(rows, "prompt_tokens") : null} />
    <StatCard label="输出 Token" value={loaded ? sum(rows, "completion_tokens") : null} />
  </div>;
}
const COLUMNS: ColumnsType<CostBucket> = [
  { title: "用途 / 模型", key: "identity", render: (_, row) => row.purpose ? purposeLabel(row.purpose) : row.model || "其他" },
  { title: "调用次数", dataIndex: "calls", align: "right", render: (value) => value == null ? "—" : formatNumber(value) },
  { title: "输入 Token", dataIndex: "prompt_tokens", align: "right", render: (value) => value == null ? "—" : formatNumber(value) },
  { title: "输出 Token", dataIndex: "completion_tokens", align: "right", render: (value) => value == null ? "—" : formatNumber(value) },
  { title: "预估费用（USD）", dataIndex: "estimated_usd", align: "right", render: (value) => value == null ? "—" : formatUsd(value) },
];

export function CostsPage() {
  const query = useCostSummary();
  const purposes = query.data?.by_purpose ?? [];
  const models = query.data?.by_model ?? [];
  const rows = purposes.length ? purposes : models;
  const calls = purposes.map((row, index) => ({ key: row.purpose ?? String(index), label: purposeLabel(row.purpose ?? "其他"), value: row.calls }));
  return <div className="af-page"><PageHeader title="成本分析" subtitle="核对累计模型费用，定位主要调用来源。"
    actions={<RefreshButton query={query} />} /><QueryFeedback query={query} /><CostMetrics rows={rows} loaded={Boolean(query.data)} />
    <div className="af-work-stack"><WorkspacePanel title="调用与费用明细">
      <DataTable query={query} dataSource={rows} columns={COLUMNS} pagination={false}
        rowKey={(row, index) => row.purpose ?? row.model ?? String(index)} emptyTitle="尚无费用记录"
        emptyDescription="产生模型调用后，可在这里查看估算费用。" /></WorkspacePanel>
      <WorkspacePanel title="费用来源"><Tabs items={[
        { key: "models", label: "按模型", children: <HBarChart data={chart(models, "model")} format="usd" /> },
        { key: "purposes", label: "按用途", children: <HBarChart data={chart(purposes, "purpose")} format="usd" /> },
        { key: "calls", label: "调用次数", children: <HBarChart data={calls} /> },
      ]} /></WorkspacePanel>
    </div>
  </div>;
}
