import { ConfigurationWorkspace } from "../../components/admin/record-workspace";
import { useState } from "react";
import { Button } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatusBadge } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel, EmptyState } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { JsonView } from "../../components/common/json";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useConnectors, useInvokeConnector } from "../../hooks/use-governance";
import type { Connector } from "../../api/types";

type ConnectorActions = { busy: boolean; invoke: (name: string) => Promise<unknown> };

function connectorColumns(actions: ConnectorActions): ColumnsType<Connector> {
  return [
    { title: "连接器", dataIndex: "name", render: (name, row) => <div className="af-record-title">
      <strong>{name}</strong><small>{row.description || "未填写说明"}</small></div> },
    { title: "服务地址", dataIndex: "base_url", render: (value) => <p className="af-record-copy">{value}</p> },
    { title: "状态", dataIndex: "enabled", render: (value) => <StatusBadge value={value ? "enabled" : "disabled"} /> },
    { title: "操作", key: "invoke", render: (_, row) => <Button size="small" disabled={actions.busy || !row.enabled}
      onClick={() => void actions.invoke(row.name)}>试调用</Button> },
  ];
}

export function ConnectorsPage() {
  const query = useConnectors();
  const invoke = useInvokeConnector();
  const feedback = useActionFeedback();
  const [result, setResult] = useState<{ name: string; data: Record<string, unknown> }>();
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["name", "description", "base_url"] });
  async function call(name: string) {
    setResult(undefined);
    await feedback.run(async () => {
      const data = await invoke.mutateAsync(name);
      setResult({ name, data });
    }, "调用已完成，请在调用响应中查看内容。");
  }
  return <div className="af-page"><PageHeader title="业务连接器" subtitle="查看外部服务配置，按连接器核对试调用响应。"
    actions={<RefreshButton query={query} />} /><ActionFeedback state={feedback} />
    <ConfigurationWorkspace editor={<WorkspacePanel title={result ? result.name + " · 调用响应" : "调用响应"}>
      {result ? <JsonView data={result.data} title="服务响应" /> : <EmptyState title={feedback.busy ? "正在等待服务响应…" : "选择一个连接器试调用"}
        description="响应会保留在这里，便于核对返回字段。" />}
    </WorkspacePanel>}><WorkspacePanel title="已配置的连接器" description="试调用使用空参数；调用行为由连接器实现决定。">
      <FilterBar {...filter} placeholder="搜索名称、地址或说明" count={query.data ? filter.rows.length : undefined} />
      <DataTable query={query} dataSource={filter.rows} columns={connectorColumns({ busy: feedback.busy, invoke: call })}
        emptyTitle={filter.filtered ? "没有匹配的连接器" : "尚未配置业务连接器"} emptyDescription="配置外部服务后，可在这里检查状态与响应。" />
    </WorkspacePanel></ConfigurationWorkspace>
  </div>;
}
