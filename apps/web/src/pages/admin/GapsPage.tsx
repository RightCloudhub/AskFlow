import { RecordWorkspace } from "../../components/admin/record-workspace";
import { Button, Popconfirm, Space } from "antd";
import { Link } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatusBadge, gapReason } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useDismissGap, useGaps, usePromoteGap } from "../../hooks/use-knowledge";
import type { Gap } from "../../api/types";

type GapActions = { busy: boolean; promote: (row: Gap) => Promise<unknown>; dismiss: (id: string) => Promise<unknown> };

function gapColumns(actions: GapActions): ColumnsType<Gap> {
  return [
    { title: "未覆盖的问题", dataIndex: "question", render: (value) => <p className="af-record-copy">{value}</p> },
    { title: "出现次数", dataIndex: "hit_count", align: "right" },
    { title: "需要补充什么", dataIndex: "reason", render: (value) => {
      const reason = gapReason(value);
      return <div className="af-record-title"><strong>{reason.label}</strong><small>{reason.hint}</small></div>;
    } },
    { title: "状态", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
    { title: "操作", key: "actions", render: (_, row) => <Space>
      <Button size="small" disabled={actions.busy} onClick={() => void actions.promote(row)}>生成草稿</Button>
      <Popconfirm title="忽略这条知识缺口？" description="记录将标记为已忽略，可继续在列表中查看。" okText="确认忽略" cancelText="保留"
        onConfirm={() => actions.dismiss(row.id)}><Button size="small" disabled={actions.busy}>忽略</Button></Popconfirm>
    </Space> },
  ];
}

export function GapsPage() {
  const query = useGaps();
  const dismiss = useDismissGap();
  const promote = usePromoteGap();
  const feedback = useActionFeedback();
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["question", "reason"], statusField: "status" });
  const columns = gapColumns({ busy: feedback.busy,
    promote: (row) => feedback.run(() => promote.mutateAsync(row), "草稿已生成，请到知识草稿中审核。"),
    dismiss: (id) => feedback.run(() => dismiss.mutateAsync(id), "知识缺口已标记为忽略。") });
  return <div className="af-page"><PageHeader title="知识缺口" subtitle="从客户未得到回答的问题中，确定下一份知识资料。"
    actions={<RefreshButton query={query} />} /><ActionFeedback state={feedback} />
    <RecordWorkspace rows={query.data} field="status" states={[{ value: "open", label: "开放问题" }, { value: "dismissed", label: "已忽略" }]}
      selected={filter.status} onSelect={filter.onStatus}>
      <WorkspacePanel title="待补充的知识" actions={<Link to="/admin/drafts">审核知识草稿</Link>}>
      <FilterBar {...filter} placeholder="搜索客户问题或原因" count={query.data ? filter.rows.length : undefined}
        options={[{ value: "all", label: "全部状态" }, { value: "open", label: "开放" }, { value: "dismissed", label: "已忽略" }]} />
      <DataTable query={query} dataSource={filter.rows} columns={columns} emptyTitle={filter.filtered ? "没有匹配的问题" : "暂无知识缺口"}
        emptyDescription={filter.filtered ? "尝试调整关键词或清除筛选。" : "未覆盖的问题会在客服对话后沉淀到这里。"} />
    </WorkspacePanel>
    </RecordWorkspace>
  </div>;
}
