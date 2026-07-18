import { FormEvent, useState } from "react";
import { Button, Card, Form, Input, Space, Table } from "antd";
import { CheckOutlined, CloseOutlined, PlusOutlined } from "@ant-design/icons";
import { PageHeader, StatusBadge } from "../../components/admin";
import {
  useApproveDraft,
  useCreateDraft,
  useDrafts,
  useRejectDraft,
} from "../../hooks/use-knowledge";
import type { Draft } from "../../api/types";

export function DraftsPage() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const draftsQ = useDrafts();
  const create = useCreateDraft();
  const approve = useApproveDraft();
  const reject = useRejectDraft();

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    await create.mutateAsync({ title, content });
    setTitle("");
    setContent("");
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="知识中心"
        title="知识草稿"
        subtitle="审核 FAQ 草稿并发布到知识库"
      />
      <Card title="新建草稿" style={{ marginBottom: 16 }}>
        <form onSubmit={(e) => void onCreate(e)}>
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
            <Button
              type="primary"
              htmlType="submit"
              icon={<PlusOutlined />}
              loading={create.isPending}
            >
              创建草稿
            </Button>
          </Form>
        </form>
      </Card>

      <Card title="草稿列表">
        <Table
          loading={draftsQ.isLoading}
          rowKey="id"
          dataSource={draftsQ.data ?? []}
          pagination={{ pageSize: 10 }}
          columns={[
            { title: "标题", dataIndex: "title" },
            {
              title: "摘要",
              dataIndex: "content",
              render: (c: string) =>
                c.slice(0, 80) + (c.length > 80 ? "…" : ""),
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
                      loading={approve.isPending && approve.variables === d.id}
                      onClick={() => void approve.mutateAsync(d.id)}
                    >
                      通过
                    </Button>
                    <Button
                      danger
                      size="small"
                      icon={<CloseOutlined />}
                      loading={reject.isPending && reject.variables === d.id}
                      onClick={() => void reject.mutateAsync(d.id)}
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
