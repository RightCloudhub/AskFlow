import { Button, Drawer } from "antd";
import { useState } from "react";
import type { ColumnsType } from "antd/es/table";
import { PageHeader } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { JsonView } from "../../components/common/json";
import { useAuditLogs } from "../../hooks/use-governance";
import type { AuditLog } from "../../api/types";
import { formatDateTime } from "../../utils";

function auditColumns(open: (row: AuditLog) => void): ColumnsType<AuditLog> {
  return [
    { title: "操作", dataIndex: "action", render: (value) => <strong className="af-record-number">{value}</strong> },
    { title: "关联资源", key: "resource", render: (_, row) => <div className="af-record-title">
      <strong>{row.resource_type}</strong><small>{row.resource_id || "未记录资源编号"}</small></div> },
    { title: "操作时间", dataIndex: "created_at", render: (value) => <span className="af-nowrap">{formatDateTime(value, true)}</span> },
    { title: "详情", key: "detail", render: (_, row) => <Button size="small" onClick={() => open(row)}>查看记录</Button> },
  ];
}

export function AuditPage() {
  const query = useAuditLogs();
  const [selected, setSelected] = useState<AuditLog | null>(null);
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["action", "resource_type", "resource_id"] });
  return <div className="af-page"><PageHeader title="审计日志" subtitle="按操作和关联资源追溯关键变更，展开记录查看原始详情。"
    actions={<RefreshButton query={query} />} />
    <WorkspacePanel title="关键操作记录">
      <FilterBar {...filter} placeholder="搜索操作、资源类型或编号" count={query.data ? filter.rows.length : undefined} />
      <DataTable query={query} dataSource={filter.rows} columns={auditColumns(setSelected)}
        emptyTitle={filter.filtered ? "没有匹配的审计记录" : "暂无关键操作记录"}
        emptyDescription={filter.filtered ? "试试更短的操作名称或资源编号。" : "有记录的业务操作发生后，会在这里显示。"} />
    </WorkspacePanel>
    <Drawer title="审计记录详情" open={Boolean(selected)} onClose={() => setSelected(null)} size="min(600px, 100vw)">
      {selected && <div className="af-work-stack"><div className="af-record-title"><strong>{selected.action}</strong>
        <small>{formatDateTime(selected.created_at, true)}</small></div><JsonView data={selected.detail} title="操作详情" /></div>}
    </Drawer>
  </div>;
}
