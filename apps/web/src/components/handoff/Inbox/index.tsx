import { Button, Space, Table, Tag, Typography } from "antd";
import { RollbackOutlined, UserSwitchOutlined } from "@ant-design/icons";
import { StatusBadge, formatWaiting, intentLabel } from "../../admin";
import type { Handoff } from "../../../api/types";
import { handoffActions } from "../actions";

type HandoffInboxProps = {
  rows: Handoff[];
  loading?: boolean;
  /** The signed-in agent; only they can return a session they claimed. */
  currentUserId?: string | null;
  claimingId?: string | null;
  returningId?: string | null;
  onClaim: (id: string) => void;
  onReturn: (id: string) => void;
  onSelect?: (row: Handoff) => void;
};

export function HandoffInbox({
  rows,
  loading,
  currentUserId,
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
          width: 100,
          render: (s: string) => <StatusBadge value={s} />,
        },
        {
          title: "客户",
          dataIndex: "user_name",
          width: 120,
          render: (v: string | null | undefined, h: Handoff) => (
            <Typography.Text strong title={h.conversation_id}>
              {v || "访客"}
            </Typography.Text>
          ),
        },
        {
          title: "意图",
          dataIndex: "intent",
          width: 100,
          render: (v: string | undefined) => intentLabel(v || "handoff"),
        },
        { title: "摘要", dataIndex: "summary" },
        {
          title: "等待",
          dataIndex: "created_at",
          width: 120,
          render: (v: string | undefined, h: Handoff) =>
            h.status === "queued" ? formatWaiting(v) : "—",
        },
        {
          title: "认领人",
          dataIndex: "claimed_by_name",
          width: 110,
          render: (v: string | null | undefined, h: Handoff) => {
            if (!h.claimed_by) return "—";
            if (h.claimed_by === currentUserId) return <Tag color="blue">我</Tag>;
            return <Tag>{v || "其他坐席"}</Tag>;
          },
        },
        {
          title: "操作",
          key: "actions",
          width: 150,
          render: (_: unknown, h: Handoff) => {
            const can = handoffActions(h, currentUserId);
            return (
              <Space onClick={(e) => e.stopPropagation()}>
                {can.claim ? (
                  <Button
                    type="primary"
                    size="small"
                    icon={<UserSwitchOutlined />}
                    loading={claimingId === h.id}
                    onClick={() => onClaim(h.id)}
                  >
                    认领
                  </Button>
                ) : null}
                {can.ret ? (
                  <Button
                    size="small"
                    icon={<RollbackOutlined />}
                    loading={returningId === h.id}
                    onClick={() => onReturn(h.id)}
                  >
                    交还 AI
                  </Button>
                ) : null}
                {can.claimedByOther ? (
                  <Typography.Text type="secondary">已被认领</Typography.Text>
                ) : null}
              </Space>
            );
          },
        },
      ]}
      locale={{ emptyText: "暂无接管会话" }}
    />
  );
}
