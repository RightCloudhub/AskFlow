import { useState } from "react";
import { Button, Card, Input, Space, Table, Typography, message } from "antd";
import { CloudUploadOutlined, ReloadOutlined } from "@ant-design/icons";
import { PageHeader } from "../../components/admin";
import { promptService } from "../../services/prompt-service";
import { usePromptTemplates, usePublishPrompt } from "../../hooks/use-ops";

export function PromptsPage() {
  const [key, setKey] = useState("rag.system");
  const [content, setContent] = useState("");
  const [active, setActive] = useState("");
  const [loadingActive, setLoadingActive] = useState(false);
  const templatesQ = usePromptTemplates();
  const publish = usePublishPrompt();

  async function loadActive() {
    setLoadingActive(true);
    try {
      const res = await promptService.active(key);
      setActive(res.content);
      setContent(res.content);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoadingActive(false);
    }
  }

  async function onPublish() {
    await publish.mutateAsync({ key, content });
    setActive(content);
    message.success("已发布并激活");
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
            <Button
              icon={<ReloadOutlined />}
              loading={loadingActive}
              onClick={() => void loadActive()}
            >
              加载当前版本
            </Button>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              loading={publish.isPending}
              onClick={() => void onPublish()}
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
          loading={templatesQ.isLoading}
          rowKey="id"
          dataSource={templatesQ.data ?? []}
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
