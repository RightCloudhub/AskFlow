import { ConfigurationWorkspace } from "../../components/admin/record-workspace";
import type { ColumnsType } from "antd/es/table";
import { PageHeader } from "../../components/admin";
import { DataTable, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { PromptEditor } from "./prompt-editor";
import { usePromptTemplates } from "../../hooks/use-ops";
import type { PromptTemplate } from "../../api/types";

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
