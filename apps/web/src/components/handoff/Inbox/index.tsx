import { Button, Space } from "antd";
import type { ColumnsType } from "antd/es/table";
import { StatusBadge, formatWaiting, intentLabel } from "../../admin";
import { DataTable, type QueryPresentation } from "../../admin/workspace";
import type { Handoff } from "../../../api/types";
import { handoffActions } from "../actions";

type HandoffInboxProps = {
  rows: Handoff[]; loading?: boolean; query?: QueryPresentation; currentUserId?: string | null;
  onSelect: (row: Handoff) => void;
};

function HandoffActions({ row, props }: { row: Handoff; props: HandoffInboxProps }) {
  const can = handoffActions(row, props.currentUserId);
  return <Space><Button size="small" onClick={() => props.onSelect(row)}>
    {can.claim ? "核对并认领" : can.ret ? "继续服务" : "查看会话"}</Button>
    {can.claimedByOther && <span className="af-record-secondary">其他座席处理中</span>}
  </Space>;
}

function inboxColumns(props: HandoffInboxProps): ColumnsType<Handoff> {
  return [
    { title: "客户与问题", key: "customer", render: (_, row) => <div className="af-record-title">
      <strong>{row.user_name || "访客"} · {intentLabel(row.intent || "handoff")}</strong>
      <small>{row.summary || "暂未生成问题摘要"}</small></div> },
    { title: "状态", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
    { title: "已等待", dataIndex: "created_at", render: (value, row) => row.status === "queued" ? formatWaiting(value) : "—" },
    { title: "认领座席", key: "owner", render: (_, row) => row.claimed_by ?
      row.claimed_by === props.currentUserId ? "我" : row.claimed_by_name || "其他座席" : "未认领" },
    { title: "服务操作", key: "actions", render: (_, row) => <HandoffActions row={row} props={props} /> },
  ];
}

export function HandoffInbox(props: HandoffInboxProps) {
  return <DataTable query={props.query} loading={props.loading ?? props.query?.isLoading} dataSource={props.rows}
    columns={inboxColumns(props)} emptyTitle="没有符合条件的接管会话"
    emptyDescription="客户转人工后，会在这里等待座席认领。" />;
}
