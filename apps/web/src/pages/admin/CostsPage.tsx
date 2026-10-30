import { PageHeader, StatCard, DonutChart, HBarChart, formatNumber, formatUsd, purposeLabel } from "../../components/admin";
import type { ChartDatum } from "../../components/admin";
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
    <StatCard label="预估总费用" value={loaded ? sum(rows, "estimated_usd") : null} format="usd" hint="USD · 以调用记录估算" />
    <StatCard label="模型调用次数" value={loaded ? sum(rows, "calls") : null} />
    <StatCard label="输入 Token" value={loaded ? sum(rows, "prompt_tokens") : null} />
    <StatCard label="输出 Token" value={loaded ? sum(rows, "completion_tokens") : null} />
  </div>;
}
const COLUMNS: ColumnsType<CostBucket> = [
  { title: "用途", dataIndex: "purpose", render: (value) => purposeLabel(value ?? "其他") },
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
  const total = query.data ? sum(rows, "estimated_usd") : null;
  const calls = purposes.map((row, index) => ({ key: row.purpose ?? String(index), label: purposeLabel(row.purpose ?? "其他"), value: row.calls }));
  return <div className="af-page"><PageHeader title="成本分析" subtitle="定位主要费用来源，按用途核对调用次数与 Token 消耗。"
    actions={<RefreshButton query={query} />} /><QueryFeedback query={query} /><CostMetrics rows={rows} loaded={Boolean(query.data)} />
    <div className="af-work-stack">
      <div className="af-dashboard-grid"><WorkspacePanel title="费用按模型分布" description="优先查看费用最高的模型。">
        {query.isLoading ? <p className="af-work-help">正在读取费用记录…</p> : <HBarChart data={chart(models, "model")} format="usd" />}
      </WorkspacePanel><WorkspacePanel title="费用按用途分布">
        <DonutChart data={chart(purposes, "purpose")} centerLabel="预估费用 · USD" centerValue={total == null ? "—" : formatUsd(total)} />
      </WorkspacePanel></div>
      <WorkspacePanel title="用途与调用明细"><DataTable dataSource={purposes} columns={COLUMNS} loading={query.isLoading} pagination={false}
        rowKey={(row, index) => row.purpose ?? row.model ?? String(index)} emptyTitle={query.isError ? "费用记录未加载" : "尚无费用记录"}
        emptyDescription="产生模型调用后，可在这里查看估算费用。" /></WorkspacePanel>
      <WorkspacePanel title="调用次数按用途分布"><HBarChart data={calls} /></WorkspacePanel>
    </div>
  </div>;
}
