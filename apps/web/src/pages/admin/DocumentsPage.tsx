import { DragEvent, FormEvent, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Input,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  DeleteOutlined,
  HistoryOutlined,
  InboxOutlined,
  ReloadOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { DocumentRevisionDrawer } from "../../components/admin/DocumentRevisionDrawer";
import { PageHeader, StatusBadge } from "../../components/admin";
import { QueryState } from "../../components/common/QueryState";
import {
  useDeleteDocument,
  useDocuments,
  useUploadDocument,
} from "../../hooks/use-documents";
import type { DocumentRow } from "../../api/types";

const { Text } = Typography;

export function DocumentsPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [selected, setSelected] = useState<DocumentRow | null>(null);

  const docsQ = useDocuments();
  const uploadM = useUploadDocument();
  const deleteM = useDeleteDocument();

  async function uploadFile(file: File) {
    setLocalError(null);
    const fd = new FormData();
    if (title.trim()) fd.set("title", title.trim());
    fd.set("file", file);
    try {
      await uploadM.mutateAsync(fd);
      setTitle("");
      if (fileRef.current) fileRef.current.value = "";
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : "上传失败");
    }
  }

  function onFormSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setLocalError("请选择文件");
      return;
    }
    void uploadFile(file);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void uploadFile(file);
  }

  async function onDelete(id: string) {
    try {
      await deleteM.mutateAsync(id);
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : "删除失败");
    }
  }

  const errorMsg =
    localError ||
    (docsQ.isError && docsQ.error instanceof Error
      ? docsQ.error.message
      : null);

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="知识中心"
        title="知识文档"
        subtitle="上传、索引、版本回滚与分块差异（对齐 RAGFlow 知识库体验）"
        actions={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => void docsQ.refetch()}
            loading={docsQ.isFetching}
          >
            刷新
          </Button>
        }
      />

      {errorMsg ? (
        <Alert
          type="error"
          showIcon
          message={errorMsg}
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setLocalError(null)}
        />
      ) : null}

      <Card title="上传并索引" style={{ marginBottom: 16 }}>
        <form onSubmit={onFormSubmit}>
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="标题（可选）"
              style={{ maxWidth: 360 }}
            />
            <div
              className={`af-upload-zone ${dragOver ? "dragover" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") fileRef.current?.click();
              }}
            >
              <InboxOutlined style={{ fontSize: 32, color: "var(--brand)" }} />
              <p>拖拽文件到此处，或点击选择</p>
              <Text type="secondary">支持常见文档格式；上传后自动分块索引</Text>
              <input
                ref={fileRef}
                name="file"
                type="file"
                required
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void uploadFile(f);
                }}
              />
            </div>
            <Button
              type="primary"
              htmlType="submit"
              icon={<UploadOutlined />}
              loading={uploadM.isPending}
            >
              上传并索引
            </Button>
          </Space>
        </form>
      </Card>

      <Card title="文档列表" extra={<Tag>{docsQ.data?.length ?? 0} 篇</Tag>}>
        <QueryState isLoading={docsQ.isLoading} isError={false}>
          <Table<DocumentRow>
            rowKey="id"
            dataSource={docsQ.data ?? []}
            loading={docsQ.isFetching && !docsQ.isLoading}
            pagination={{ pageSize: 10 }}
            columns={[
              {
                title: "标题",
                dataIndex: "title",
                render: (t: string) => t || "—",
              },
              { title: "文件名", dataIndex: "filename" },
              {
                title: "状态",
                dataIndex: "status",
                render: (s: string) => <StatusBadge value={s} />,
              },
              {
                title: "分块",
                dataIndex: "chunk_count",
                width: 80,
                render: (n: number) => (
                  <Tag color={n > 0 ? "blue" : "default"}>{n}</Tag>
                ),
              },
              {
                title: "Gen",
                dataIndex: "generation",
                width: 70,
                render: (g: number | undefined) => g ?? "—",
              },
              {
                title: "操作",
                key: "actions",
                width: 200,
                render: (_: unknown, d: DocumentRow) => (
                  <Space>
                    <Button
                      size="small"
                      icon={<HistoryOutlined />}
                      onClick={() => setSelected(d)}
                    >
                      版本
                    </Button>
                    <Button
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      loading={deleteM.isPending && deleteM.variables === d.id}
                      onClick={() => void onDelete(d.id)}
                    >
                      删除
                    </Button>
                  </Space>
                ),
              },
            ]}
            locale={{ emptyText: "暂无文档 — 上传后将出现在此列表" }}
          />
        </QueryState>
      </Card>

      <DocumentRevisionDrawer
        doc={selected}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
