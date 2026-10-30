import { RecordWorkspace } from "../../components/admin/record-workspace";
import { useState } from "react";
import { Button, Drawer } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, PriorityTag, StatusBadge, ticketTypeLabel } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { useAdminTickets } from "../../hooks/use-ops";
import type { AdminTicket } from "../../api/types";

import { TicketResolutionFlow } from "./ticket-resolution-flow";

type TicketActions = { busy: boolean; select: (ticket: AdminTicket) => void };

function ticketColumns(actions: TicketActions): ColumnsType<AdminTicket> {
  return [
    { title: "客户问题", dataIndex: "title", render: (title, row) => <div className="af-record-title">
      <strong>{title}</strong><small>{ticketTypeLabel(row.type)} · {row.assignee ? "负责人：" + row.assignee : "尚未分配负责人"}</small></div> },
    { title: "状态", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
    { title: "优先级", dataIndex: "priority", render: (value) => <PriorityTag value={value} /> },
    { title: "处理", key: "action", render: (_, row) => <Button size="small" disabled={actions.busy} onClick={() => actions.select(row)}>查看并处理</Button> },
  ];
}

export function TicketsAdminPage() {
  const query = useAdminTickets();
  const [selected, setSelected] = useState<AdminTicket>();
  const [busy, setBusy] = useState(false);
  const current = query.data?.find((ticket) => ticket.id === selected?.id) ?? selected;
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["title", "id", "assignee"], statusField: "status" });
  const actions: TicketActions = { busy, select: setSelected };
  return <div className="af-page"><PageHeader title="工单中心" subtitle="找到待处理的问题，明确负责人和下一步操作。"
    actions={<RefreshButton query={query} />} />
    <RecordWorkspace rows={query.data} field="status" states={[{ value: "pending", label: "待处理" }, { value: "processing", label: "处理中" }, { value: "resolved", label: "已解决" }]}
      selected={filter.status} onSelect={filter.onStatus}>
      <WorkspacePanel title="客服工单">
      <FilterBar {...filter} placeholder="搜索问题、工单编号或负责人" count={query.data ? filter.rows.length : undefined}
        options={[{ value: "all", label: "全部状态" }, { value: "pending", label: "待处理" }, { value: "processing", label: "处理中" },
          { value: "resolved", label: "已解决" }, { value: "closed", label: "已关闭" }]} />
      <DataTable query={query} dataSource={filter.rows} columns={ticketColumns(actions)}
        emptyTitle={filter.filtered ? "没有匹配的工单" : "当前没有客服工单"}
        emptyDescription={filter.filtered ? "调整关键词或状态，查看其他工单。" : "客户提交或系统创建的工单会显示在这里。"} />
    </WorkspacePanel>
    </RecordWorkspace><Drawer title="工单处理" open={Boolean(selected)}
      onClose={() => { if (!busy) setSelected(undefined); }} closable={!busy} keyboard={!busy} mask={{ closable: !busy }} destroyOnHidden>
      {current && <TicketResolutionFlow key={current.id} ticket={current} onBusyChange={setBusy}
        onClose={() => { if (!busy) setSelected(undefined); }} />}
    </Drawer>
  </div>;
}
