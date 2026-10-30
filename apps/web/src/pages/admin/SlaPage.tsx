import { useState } from "react";
import { Button, Drawer } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatCard, DonutChart, StatusBadge, PriorityTag } from "../../components/admin";
import { BRAND } from "../../components/admin/theme";
import { DataTable, QueryFeedback, WorkspacePanel, EmptyState } from "../../components/admin/workspace";
import { useSlaStatus } from "../../hooks/use-ops";
import type { SlaScanResult, SlaStatus } from "../../api/types";

import { ScanChanges, SlaScanFlow, SLA_LABELS as LABELS } from "./sla-scan-flow";

const COLORS: Record<string, string> = { ok: BRAND.accent, normal: BRAND.accent, warning: BRAND.warning, breached: BRAND.danger };
const COLUMNS: ColumnsType<SlaStatus["tickets"][number]> = [
  { title: "工单问题", dataIndex: "title" },
  { title: "SLA 状态", dataIndex: "sla_state", render: (value) => <StatusBadge value={value} /> },
  { title: "优先级", dataIndex: "priority", render: (value) => <PriorityTag value={value} /> },
  { title: "处理状态", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
];

function ScanResults({ scan }: { scan: SlaScanResult | null }) {
  return <WorkspacePanel title="本次扫描结果" description={scan ? "已记录 " + scan.scanned_changes + " 项状态变更。" : "扫描会检查 SLA 状态，并触发相应通知。"}>
    {scan ? <ScanChanges scan={scan} /> :
      <EmptyState title="还未执行本次扫描" description="点击“扫描并通知”后，可在这里查看变更明细。" />}
  </WorkspacePanel>;
}

export function SlaPage() {
  const query = useSlaStatus();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [scan, setScan] = useState<SlaScanResult | null>(null);
  const counts = query.data?.counts ?? {};
  const chart = Object.entries(counts).map(([key, value]) => ({ key, label: LABELS[key] ?? key, value, color: COLORS[key] }));
  return <div className="af-page"><PageHeader title="SLA 监控" subtitle="优先处理预警和违约工单，核对每次扫描产生的变更。"
    actions={<Button type="primary" onClick={() => setOpen(true)}>扫描并通知</Button>} />
    <QueryFeedback query={query} />
    {chart.length > 0 && <div className="af-dashboard-metrics af-metrics-fluid">{Object.entries(counts).map(([key, value]) =>
      <StatCard key={key} label={LABELS[key] ?? key} value={value} />)}</div>}
    <div className="af-sla-workspace"><WorkspacePanel title="预警与违约工单">
      <DataTable query={query} dataSource={query.data?.tickets ?? []} columns={COLUMNS}
        emptyTitle="当前没有预警或违约工单" emptyDescription="接近或超过服务时限的工单会显示在这里。" />
    </WorkspacePanel><div className="af-sla-aside"><WorkspacePanel title="服务时限状态分布">
      <DonutChart data={chart} centerLabel="工单" centerValue={query.data ? String(Object.values(counts).reduce((sum, value) => sum + value, 0)) : "—"} />
    </WorkspacePanel><ScanResults scan={scan} /></div></div>
    <Drawer title="SLA 扫描" open={open} onClose={() => { if (!busy) setOpen(false); }}
      closable={!busy} keyboard={!busy} mask={{ closable: !busy }} destroyOnHidden>
      <SlaScanFlow onResult={setScan} onBusyChange={setBusy} onClose={() => setOpen(false)} />
    </Drawer>
  </div>;
}
