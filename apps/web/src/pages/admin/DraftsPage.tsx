import { FormEvent, useEffect, useState } from "react";
import { Button, Card, Form, Input, Space, Table } from "antd";
import { CheckOutlined, CloseOutlined, PlusOutlined } from "@ant-design/icons";
import { api } from "../../api/client";
import { PageHeader, StatusBadge } from "../../components/admin";

type Draft = {
  id: string;
  title: string;
  content: string;
  status: string;
  document_id: string | null;
};

export function DraftsPage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setDrafts(await api<Draft[]>("/api/v1/admin/drafts"));
  }

  useEffect(() => {
    void load().finally(() => setLoading(false));
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    await api("/api/v1/admin/drafts", {
      method: "POST",
      body: JSON.stringify({ title, content }),
    });
    setTitle("");
    setContent("");
    await load();
  }

  async function approve(id: string) {
    await api(`/api/v1/admin/drafts/${id}/approve`, { method: "POST" });
    await load();
  }

  async function reject(id: string) {
    await api(`/api/v1/admin/drafts/${id}/reject`, { method: "POST" });
    await load();
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="知识中心"
        title="知识草稿"
        subtitle="审核 FAQ 草稿并发布到知识库"
      />
      <Card title="新建草稿" style={{ marginBottom: 16 }}>
        <form onSubmit={(e) => void create(e)}>
          <Form layout="vertical">
            <Form.Item label="标题" required>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="标题"
                required
              />
            </Form.Item>
            <Form.Item label="正文" required>
              <Input.TextArea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="正文"
                rows={4}
                required
              />
            </Form.Item>
            <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
              创建草稿
            </Button>
          </Form>
        </form>
      </Card>

      <Card title="草稿列表">
        <Table
          loading={loading}
          rowKey="id"
          dataSource={drafts}
          pagination={{ pageSize: 10 }}
          columns={[
            { title: "标题", dataIndex: "title" },
            {
              title: "摘要",
              dataIndex: "content",
              render: (c: string) => c.slice(0, 80) + (c.length > 80 ? "…" : ""),
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 100,
              render: (s: string) => <StatusBadge value={s} />,
            },
            {
              title: "操作",
              key: "actions",
              width: 200,
              render: (_: unknown, d: Draft) =>
                d.status === "draft" ? (
                  <Space>
                    <Button
                      type="primary"
                      size="small"
                      icon={<CheckOutlined />}
                      onClick={() => void approve(d.id)}
                    >
                      通过
                    </Button>
                    <Button
                      danger
                      size="small"
                      icon={<CloseOutlined />}
                      onClick={() => void reject(d.id)}
                    >
                      拒绝
                    </Button>
                  </Space>
                ) : (
                  "—"
                ),
            },
          ]}
          locale={{ emptyText: "暂无草稿" }}
        />
      </Card>
    </div>
  );
}
