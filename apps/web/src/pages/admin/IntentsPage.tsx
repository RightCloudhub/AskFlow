import { ConfigurationWorkspace } from "../../components/admin/record-workspace";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatusBadge } from "../../components/admin";
import { intentLabel } from "../../components/admin/labels";
import { DataTable, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useIntents } from "../../hooks/use-ops";
import type { IntentRow } from "../../api/types";

import { IntentEditor, ROUTE_LABELS } from "./intent-editor";

const COLUMNS: ColumnsType<IntentRow> = [
  { title: "客户意图", dataIndex: "intent", render: (value) => intentLabel(value) },
  { title: "处理方式", dataIndex: "route", render: (value) => ROUTE_LABELS[value] ?? value },
  { title: "状态", dataIndex: "enabled", render: (value) => <StatusBadge value={value ? "enabled" : "disabled"} /> },
  { title: "说明", dataIndex: "description" },
];

export function IntentsPage() {
  const query = useIntents();
  return <div className="af-page"><PageHeader title="意图路由" subtitle="决定不同客户问题进入知识问答、工具、工单或人工处理。"
    actions={<RefreshButton query={query} />} />
    <ConfigurationWorkspace editor={<IntentEditor />}><WorkspacePanel title="当前意图映射">
      <DataTable query={query} columns={COLUMNS} dataSource={query.data ?? []} pagination={false}
        emptyTitle="尚未配置运营映射" emptyDescription="选择意图并保存处理方式，即可建立映射记录。" />
    </WorkspacePanel></ConfigurationWorkspace>
  </div>;
}
