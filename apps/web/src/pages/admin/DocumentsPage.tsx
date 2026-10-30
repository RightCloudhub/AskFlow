import { ConfigurationWorkspace } from "../../components/admin/record-workspace";
import { useState } from "react";
import { Button, Popconfirm, Space } from "antd";
import { Link } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import { DocumentRevisionDrawer } from "../../components/admin/DocumentRevisionDrawer";
import { PageHeader, StatusBadge } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useDeleteDocument, useDocuments } from "../../hooks/use-documents";
import type { DocumentRow } from "../../api/types";
import { DocumentUpload } from "./document-upload";

const STATUSES = [{ value: "all", label: "全部状态" }, { value: "indexed", label: "已索引" },
  { value: "indexing", label: "索引中" }, { value: "failed", label: "索引失败" }];
type DocumentActions = { busy: boolean; open: (doc: DocumentRow) => void; remove: (id: string) => Promise<unknown> };

function documentColumns(actions: DocumentActions): ColumnsType<DocumentRow> {
  return [
    { title: "文档", dataIndex: "title", render: (title: string, row) => <div className="af-record-title">
      <strong>{title || row.filename}</strong><small>{row.filename}</small>
      {row.error_message && <small className="af-score--danger">{row.error_message}</small>}
    </div> },
    { title: "索引状态", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
    { title: "知识分块", dataIndex: "chunk_count", align: "right", render: (value) => value ?? "—" },
    { title: "当前版本", dataIndex: "generation", align: "right", render: (value) => value ?? "—" },
    { title: "操作", key: "actions", render: (_, row) => <Space>
      <Button size="small" onClick={() => actions.open(row)}>查看版本</Button>
      <Popconfirm title="删除这篇知识文档？" description="文档及其检索索引会一起删除。" okText="删除文档" cancelText="保留"
        okButtonProps={{ danger: true }} onConfirm={() => actions.remove(row.id)}>
        <Button size="small" danger disabled={actions.busy}>删除</Button>
      </Popconfirm>
    </Space> },
  ];
}

export function DocumentsPage() {
  const query = useDocuments();
  const remove = useDeleteDocument();
  const feedback = useActionFeedback();
  const [selected, setSelected] = useState<DocumentRow | null>(null);
  const current = query.data?.find((doc) => doc.id === selected?.id) ?? selected;
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["title", "filename"], statusField: "status" });
  const columns = documentColumns({ busy: feedback.busy, open: setSelected,
    remove: (id) => feedback.run(() => remove.mutateAsync(id), "文档及索引已删除。") });
  return <div className="af-page">
    <PageHeader title="知识文档" subtitle="维护客服回答的依据，查看索引状态与历史版本。" actions={<RefreshButton query={query} />} />
    <ActionFeedback state={feedback} />
    <ConfigurationWorkspace editor={<DocumentUpload />}>
      <WorkspacePanel title="知识库文档" description="已索引的内容可用于知识检索。" actions={<Link to="/admin/gaps">查看知识缺口</Link>}>
        <FilterBar {...filter} placeholder="搜索标题或文件名" options={STATUSES} count={query.data ? filter.rows.length : undefined} />
        <DataTable query={query} dataSource={filter.rows} columns={columns} emptyTitle={filter.filtered ? "没有匹配的文档" : "知识库还没有文档"}
          emptyDescription={filter.filtered ? "调整关键词或状态后重试。" : "上传一份文字资料，建立客服回答的依据。"} />
      </WorkspacePanel>
    </ConfigurationWorkspace><DocumentRevisionDrawer doc={current} open={Boolean(selected)} onClose={() => setSelected(null)} />
  </div>;
}
