import { RecordWorkspace } from "../../components/admin/record-workspace";
import { Button, Popconfirm, Space } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, PriorityTag, StatusBadge, ticketTypeLabel } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useAdminTickets, useUpdateAdminTicket } from "../../hooks/use-ops";
import type { AdminTicket } from "../../api/types";

type TicketActions = { busy: boolean; update: (id: string, status: string) => Promise<unknown> };

function TicketActionsCell({ row, actions }: { row: AdminTicket; actions: TicketActions }) {
  if (row.status !== "pending" && row.status !== "processing") return <span className="af-record-secondary">已结束处理</span>;
  return <Space>
    {row.status === "pending" && <Button size="small" disabled={actions.busy}
      onClick={() => void actions.update(row.id, "processing")}>开始处理</Button>}
    <Popconfirm title="确认这张工单已解决？" description="请核对客户问题已处理，再更新工单状态。"
      okText="标记已解决" cancelText="继续处理" onConfirm={() => actions.update(row.id, "resolved")}>
      <Button size="small" disabled={actions.busy}>标记解决</Button>
    </Popconfirm>
  </Space>;
}

function ticketColumns(actions: TicketActions): ColumnsType<AdminTicket> {
  return [
    { title: "客户问题", dataIndex: "title", render: (title, row) => <div className="af-record-title">
      <strong>{title}</strong><small>{ticketTypeLabel(row.type)} · {row.assignee ? "负责人：" + row.assignee : "尚未分配负责人"}</small></div> },
    { title: "状态", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
    { title: "优先级", dataIndex: "priority", render: (value) => <PriorityTag value={value} /> },
    { title: "处理", key: "action", render: (_, row) => <TicketActionsCell row={row} actions={actions} /> },
  ];
}

export function TicketsAdminPage() {
  const query = useAdminTickets();
  const update = useUpdateAdminTicket();
  const feedback = useActionFeedback();
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["title", "id", "assignee"], statusField: "status" });
  const actions: TicketActions = { busy: feedback.busy, update: (id, status) => feedback.run(
    () => update.mutateAsync({ id, status }), status === "resolved" ? "工单已标记为解决。" : "工单已进入处理中。") };
  return <div className="af-page"><PageHeader title="工单中心" subtitle="找到待处理的问题，明确负责人和下一步操作。"
    actions={<RefreshButton query={query} />} /><ActionFeedback state={feedback} />
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
    </RecordWorkspace>
  </div>;
}
