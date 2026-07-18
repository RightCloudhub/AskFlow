import { Button, Space, Table, Tag } from "antd";
import { RollbackOutlined, UserSwitchOutlined } from "@ant-design/icons";
import { StatusBadge } from "../../admin";
import type { Handoff } from "../../../api/types";

type HandoffInboxProps = {
  rows: Handoff[];
  loading?: boolean;
  claimingId?: string | null;
  returningId?: string | null;
  onClaim: (id: string) => void;
  onReturn: (id: string) => void;
  onSelect?: (row: Handoff) => void;
};

export function HandoffInbox({
  rows,
  loading,
  claimingId,
  returningId,
  onClaim,
  onReturn,
  onSelect,
}: HandoffInboxProps) {
  return (
    <Table
      loading={loading}
      rowKey="id"
      dataSource={rows}
      pagination={{ pageSize: 10 }}
      onRow={(record) => ({
        onClick: () => onSelect?.(record),
        style: { cursor: onSelect ? "pointer" : undefined },
      })}
      columns={[
        {
          title: "状态",
          dataIndex: "status",
          width: 110,
          render: (s: string) => <StatusBadge value={s} />,
        },
        {
          title: "会话",
          dataIndex: "conversation_id",
          render: (id: string) => <code className="af-mono">{id}</code>,
        },
        {
          title: "意图",
          dataIndex: "intent",
          width: 100,
          render: (v: string | undefined) => v || "handoff",
        },
        { title: "摘要", dataIndex: "summary" },
        {
          title: "认领人",
          dataIndex: "claimed_by",
          width: 120,
          render: (v: string | null) =>
            v ? <Tag>{v.slice(0, 8)}…</Tag> : "—",
        },
        {
          title: "操作",
          key: "actions",
          width: 220,
          render: (_: unknown, h: Handoff) => (
            <Space
              onClick={(e) => e.stopPropagation()}
            >
              <Button
                type="primary"
                size="small"
                icon={<UserSwitchOutlined />}
                loading={claimingId === h.id}
                onClick={() => onClaim(h.id)}
              >
                认领
              </Button>
              <Button
                size="small"
                icon={<RollbackOutlined />}
                loading={returningId === h.id}
                onClick={() => onReturn(h.id)}
              >
                交还 AI
              </Button>
            </Space>
          ),
        },
      ]}
      locale={{ emptyText: "暂无接管会话" }}
    />
  );
}
