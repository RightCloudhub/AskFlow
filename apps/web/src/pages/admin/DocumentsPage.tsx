import { FormEvent, useEffect, useState } from "react";
import { Alert, Button, Card, Input, Space, Table, Tag } from "antd";
import { DeleteOutlined, UploadOutlined } from "@ant-design/icons";
import { getToken, api } from "../../api/client";
import { PageHeader, StatusBadge } from "../../components/admin";

type Doc = {
  id: string;
  title: string;
  filename: string;
  status: string;
  chunk_count: number;
};

export function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function load() {
    setDocs(await api<Doc[]>("/api/v1/admin/documents"));
  }

  useEffect(() => {
    void load().catch((e) => setError(String(e)));
  }, []);

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const token = getToken();
    setUploading(true);
    try {
      const res = await fetch("/api/v1/embedding/upload", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
      });
      if (!res.ok) {
        setError(await res.text());
        return;
      }
      form.reset();
      await load();
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(id: string) {
    await api(`/api/v1/admin/documents/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="知识中心"
        title="知识文档"
        subtitle="上传文档并建立检索索引"
      />
      {error ? (
        <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />
      ) : null}

      <Card title="上传并索引" style={{ marginBottom: 16 }}>
        <form onSubmit={(e) => void onUpload(e)}>
          <Space wrap align="start">
            <Input name="title" placeholder="标题（可选）" style={{ width: 240 }} />
            <input name="file" type="file" required />
            <Button type="primary" htmlType="submit" icon={<UploadOutlined />} loading={uploading}>
              上传并索引
            </Button>
          </Space>
        </form>
      </Card>

      <Card title="文档列表">
        <Table
          rowKey="id"
          dataSource={docs}
          pagination={{ pageSize: 10 }}
          columns={[
            { title: "标题", dataIndex: "title", render: (t: string) => t || "—" },
            { title: "文件名", dataIndex: "filename" },
            {
              title: "状态",
              dataIndex: "status",
              render: (s: string) => <StatusBadge value={s} />,
            },
            {
              title: "分块数",
              dataIndex: "chunk_count",
              render: (n: number) => <Tag>{n}</Tag>,
            },
            {
              title: "操作",
              key: "actions",
              render: (_: unknown, d: Doc) => (
                <Button
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => void onDelete(d.id)}
                >
                  删除
                </Button>
              ),
            },
          ]}
          locale={{ emptyText: "暂无文档" }}
        />
      </Card>
    </div>
  );
}
