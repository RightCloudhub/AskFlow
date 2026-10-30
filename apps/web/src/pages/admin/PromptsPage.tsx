import { ConfigurationWorkspace } from "../../components/admin/record-workspace";
import { useState } from "react";
import { Button, Input, Popconfirm } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader } from "../../components/admin";
import { DataTable, RefreshButton, SettingsSection, WorkspacePanel } from "../../components/admin/workspace";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { promptService } from "../../services/prompt-service";
import { usePromptTemplates, usePublishPrompt } from "../../hooks/use-ops";
import type { PromptTemplate } from "../../api/types";

const EDITOR_ROWS = { minRows: 8, maxRows: 20 };

function usePromptEditor() {
  const [key, setKey] = useState("rag.system");
  const [content, setContent] = useState("");
  const [active, setActive] = useState<{ key: string; content: string }>();
  const publish = usePublishPrompt();
  const feedback = useActionFeedback();
  async function load() {
    if (!key.trim()) return;
    const target = key.trim();
    await feedback.run(async () => {
      const result = await promptService.active(target);
      setActive({ key: target, content: result.content });
      setContent(result.content);
    }, "已载入当前生效版本。");
  }
  async function save() {
    if (!key.trim() || !content.trim()) return;
    const target = key.trim();
    const body = content;
    await feedback.run(async () => {
      await publish.mutateAsync({ key: target, content: body });
      setActive({ key: target, content: body });
    }, "新版本已发布并激活。");
  }
  return { key, setKey, content, setContent, active, feedback, load, save };
}

function PromptEditor() {
  const state = usePromptEditor();
  const current = state.active?.key === state.key.trim() ? state.active : undefined;
  return <SettingsSection title="编辑提示词" description="按模板键载入当前内容，核对后发布新版本。发布后立即生效。">
    <ActionFeedback state={state.feedback} /><div className="af-work-stack">
      <label className="af-field"><span>模板键</span><Input value={state.key} disabled={state.feedback.busy}
        onChange={(event) => { state.setKey(event.target.value); state.feedback.clear(); }} placeholder="例如：rag.system" /></label>
      <label className="af-field"><span>模板正文</span><Input.TextArea value={state.content} autoSize={EDITOR_ROWS}
        disabled={state.feedback.busy} onChange={(event) => { state.setContent(event.target.value); state.feedback.clear(); }}
        placeholder="载入当前版本，或填写完整的提示词正文" /></label>
      <div className="af-work-actions">
        <Popconfirm title="载入当前版本？" description={state.content ? "编辑区内容将替换为当前生效的版本。" : "读取这个模板当前生效的正文。"}
          okText="载入版本" cancelText="取消" onConfirm={state.load}>
          <Button disabled={!state.key.trim() || state.feedback.busy}>载入当前版本</Button></Popconfirm>
        <Popconfirm title={"发布 " + state.key.trim() + " 的新版本？"} description="新正文将立即替换当前生效内容。"
          okText="发布并激活" cancelText="继续编辑" onConfirm={state.save}>
          <Button type="primary" loading={state.feedback.busy} disabled={!state.key.trim() || !state.content.trim()}>发布并激活</Button></Popconfirm>
      </div>
      {current && <WorkspacePanel title="当前生效内容" description={state.content === current.content ? "编辑内容与生效版本一致。" : "编辑内容尚未发布。"}>
        <p className="af-work-preview">{current.content}</p>
      </WorkspacePanel>}
    </div>
  </SettingsSection>;
}

const COLUMNS: ColumnsType<PromptTemplate> = [
  { title: "模板键", dataIndex: "key" }, { title: "用途说明", dataIndex: "description" },
  { title: "当前生效版本", dataIndex: "active_version_id", render: (value) => value || "尚未激活" },
];

export function PromptsPage() {
  const query = usePromptTemplates();
  return <div className="af-page"><PageHeader title="提示词模板" subtitle="维护可追溯的模板版本，明确每次发布的目标和内容。"
    actions={<RefreshButton query={query} />} /><ConfigurationWorkspace wideEditor editor={<PromptEditor />}>
      <WorkspacePanel title="模板目录"><DataTable query={query} columns={COLUMNS} dataSource={query.data ?? []} pagination={false}
        emptyTitle="尚未配置提示词模板" emptyDescription="使用模板键编写并发布第一份正文。" /></WorkspacePanel>
    </ConfigurationWorkspace>
  </div>;
}
