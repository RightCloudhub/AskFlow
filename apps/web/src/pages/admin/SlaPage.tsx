import { useState } from "react";
import { Button, List } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatCard, DonutChart, StatusBadge, PriorityTag } from "../../components/admin";
import { BRAND } from "../../components/admin/theme";
import { DataTable, QueryFeedback, WorkspacePanel, EmptyState } from "../../components/admin/workspace";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useSlaScan, useSlaStatus } from "../../hooks/use-ops";
import type { SlaScanResult, SlaStatus } from "../../api/types";

const LABELS: Record<string, string> = { ok: "正常", normal: "正常", warning: "预警", breached: "违约", pending: "待处理", processing: "处理中" };
const COLORS: Record<string, string> = { ok: BRAND.accent, normal: BRAND.accent, warning: BRAND.warning, breached: BRAND.danger };
const COLUMNS: ColumnsType<SlaStatus["tickets"][number]> = [
  { title: "工单问题", dataIndex: "title" },
  { title: "SLA 状态", dataIndex: "sla_state", render: (value) => <StatusBadge value={value} /> },
  { title: "优先级", dataIndex: "priority", render: (value) => <PriorityTag value={value} /> },
  { title: "处理状态", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
];

function ScanResults({ scan }: { scan: SlaScanResult | null }) {
  return <WorkspacePanel title="本次扫描结果" description={scan ? "已记录 " + scan.scanned_changes + " 项状态变更。" : "扫描会检查 SLA 状态，并触发相应通知。"}>
    {scan ? <List dataSource={scan.changes} locale={{ emptyText: "本次扫描没有发现状态变更。" }}
      renderItem={(row) => <List.Item><div className="af-record-title"><strong>{row.ticket_id}</strong>
        <small>{(LABELS[row.previous] ?? row.previous) + " → " + (LABELS[row.current] ?? row.current)}</small>
        <small>{row.reason}</small></div></List.Item>} /> :
      <EmptyState title="还未执行本次扫描" description="点击“扫描并通知”后，可在这里查看变更明细。" />}
  </WorkspacePanel>;
}

export function SlaPage() {
  const query = useSlaStatus();
  const mutation = useSlaScan();
  const feedback = useActionFeedback();
  const [scan, setScan] = useState<SlaScanResult | null>(null);
  const counts = query.data?.counts ?? {};
  const chart = Object.entries(counts).map(([key, value]) => ({ key, label: LABELS[key] ?? key, value, color: COLORS[key] }));
  async function runScan() {
    await feedback.run(async () => setScan(await mutation.mutateAsync()), "扫描已完成，请查看状态变更。");
  }
  return <div className="af-page"><PageHeader title="SLA 监控" subtitle="优先处理预警和违约工单，核对每次扫描产生的变更。"
    actions={<Button type="primary" loading={feedback.busy} onClick={() => void runScan()}>扫描并通知</Button>} />
    <ActionFeedback state={feedback} /><QueryFeedback query={query} />
    {chart.length > 0 && <div className="af-dashboard-metrics af-metrics-fluid">{Object.entries(counts).map(([key, value]) =>
      <StatCard key={key} label={LABELS[key] ?? key} value={value} />)}</div>}
    <div className="af-sla-workspace"><WorkspacePanel title="预警与违约工单">
      <DataTable query={query} dataSource={query.data?.tickets ?? []} columns={COLUMNS}
        emptyTitle="当前没有预警或违约工单" emptyDescription="接近或超过服务时限的工单会显示在这里。" />
    </WorkspacePanel><div className="af-sla-aside"><WorkspacePanel title="服务时限状态分布">
      <DonutChart data={chart} centerLabel="工单" centerValue={query.data ? String(Object.values(counts).reduce((sum, value) => sum + value, 0)) : "—"} />
    </WorkspacePanel><ScanResults scan={scan} /></div></div>
  </div>;
}
