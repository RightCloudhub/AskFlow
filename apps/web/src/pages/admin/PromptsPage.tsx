import { useEffect, useState } from "react";
import { Button, Card, Input, Space, Table, Typography } from "antd";
import { CloudUploadOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "../../api/client";
import { PageHeader } from "../../components/admin";

type Template = {
  id: string;
  key: string;
  description: string;
  active_version_id: string | null;
};

export function PromptsPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [key, setKey] = useState("rag.system");
  const [content, setContent] = useState("");
  const [active, setActive] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setTemplates(await api<Template[]>("/api/v1/admin/prompts"));
  }

  useEffect(() => {
    void load().finally(() => setLoading(false));
  }, []);

  async function loadActive() {
    const res = await api<{ content: string }>(`/api/v1/admin/prompts/${key}/active`);
    setActive(res.content);
    setContent(res.content);
  }

  async function publish() {
    await api(`/api/v1/admin/prompts/${key}/versions`, {
      method: "POST",
      body: JSON.stringify({ content, activate: true }),
    });
    await load();
    await loadActive();
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="智能配置"
        title="提示词模板"
        subtitle="Prompt 版本管理与热激活"
      />
      <Card title="编辑并发布" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Input
            addonBefore="模板 Key"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          <Input.TextArea
            rows={8}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="提示词正文"
            style={{ fontFamily: "var(--font-mono, monospace)" }}
          />
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadActive()}>
              加载当前版本
            </Button>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={() => void publish()}
            >
              发布并激活
            </Button>
          </Space>
          {active ? (
            <div>
              <Typography.Text type="secondary">当前生效内容预览</Typography.Text>
              <pre className="code-block" style={{ marginTop: 8 }}>
                {active}
              </pre>
            </div>
          ) : null}
        </Space>
      </Card>

      <Card title="模板列表">
        <Table
          loading={loading}
          rowKey="id"
          dataSource={templates}
          pagination={false}
          columns={[
            { title: "Key", dataIndex: "key" },
            { title: "说明", dataIndex: "description" },
            {
              title: "激活版本",
              dataIndex: "active_version_id",
              render: (id: string | null) => id || "—",
            },
          ]}
          locale={{ emptyText: "暂无模板" }}
        />
      </Card>
    </div>
  );
}
