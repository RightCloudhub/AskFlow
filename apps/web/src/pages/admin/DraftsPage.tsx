import { ConfigurationWorkspace } from "../../components/admin/record-workspace";
import { useState } from "react";
import { Button, Drawer, Popconfirm, Space } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatusBadge } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useApproveDraft, useDrafts, useRejectDraft } from "../../hooks/use-knowledge";
import { DraftEditor } from "./draft-editor";
import type { Draft } from "../../api/types";

const SUMMARY_LENGTH = 80;
type DraftActions = { busy: boolean; open: (row: Draft) => void; approve: (id: string) => Promise<unknown>; reject: (id: string) => Promise<unknown> };

function DraftButtons({ row, actions }: { row: Draft; actions: DraftActions }) {
  if (row.status !== "draft") return <span className="af-record-secondary">已完成审核</span>;
  return <Space><Popconfirm title="审核通过并发布到知识库？" description="请先核对完整答案。发布内容将用于客服回答。"
    okText="通过并发布" cancelText="继续审核" onConfirm={() => actions.approve(row.id)}>
    <Button size="small" disabled={actions.busy}>通过并发布</Button></Popconfirm>
    <Button size="small" danger disabled={actions.busy} onClick={() => void actions.reject(row.id)}>拒绝</Button>
  </Space>;
}

function draftColumns(actions: DraftActions): ColumnsType<Draft> {
  return [
    { title: "草稿", dataIndex: "title", render: (title, row) => <div className="af-record-title"><strong>{title}</strong>
      <small>{row.content.slice(0, SUMMARY_LENGTH)}{row.content.length > SUMMARY_LENGTH ? "…" : ""}</small>
      <Button type="link" size="small" onClick={() => actions.open(row)}>查看全文</Button></div> },
    { title: "状态", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
    { title: "审核", key: "actions", render: (_, row) => <DraftButtons row={row} actions={actions} /> },
  ];
}

export function DraftsPage() {
  const query = useDrafts();
  const approve = useApproveDraft();
  const reject = useRejectDraft();
  const feedback = useActionFeedback();
  const [selected, setSelected] = useState<Draft | null>(null);
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["title", "content"], statusField: "status" });
  const actions: DraftActions = { busy: feedback.busy, open: setSelected,
    approve: (id) => feedback.run(() => approve.mutateAsync(id), "草稿已通过并发布。"),
    reject: (id) => feedback.run(() => reject.mutateAsync(id), "草稿已拒绝，记录保留在列表中。") };
  const current = query.data?.find((row) => row.id === selected?.id) ?? selected;
  return <div className="af-page"><PageHeader title="知识草稿" subtitle="核对答案再发布，让每一次知识补充有据可查。"
    actions={<RefreshButton query={query} />} /><ActionFeedback state={feedback} />
    <ConfigurationWorkspace editor={<DraftEditor />}><WorkspacePanel title="草稿审核队列">
      <FilterBar {...filter} placeholder="搜索问题或答案" count={query.data ? filter.rows.length : undefined}
        options={[{ value: "all", label: "全部状态" }, { value: "draft", label: "待审核" },
          { value: "approved", label: "已通过" }, { value: "rejected", label: "已拒绝" }]} />
      <DataTable query={query} dataSource={filter.rows} columns={draftColumns(actions)} emptyTitle={filter.filtered ? "没有匹配的草稿" : "还没有知识草稿"}
        emptyDescription="手动编写答案，或从知识缺口生成草稿后审核。" />
    </WorkspacePanel></ConfigurationWorkspace>
    <Drawer title={current?.title ?? "草稿全文"} open={Boolean(selected)} onClose={() => setSelected(null)} size="min(600px, 100vw)">
      {current && <div className="af-work-stack"><StatusBadge value={current.status} /><p className="af-work-preview">{current.content}</p>
        <ActionFeedback state={feedback} /><DraftButtons row={current} actions={actions} /></div>}
    </Drawer>
  </div>;
}
