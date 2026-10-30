import { ConfigurationWorkspace } from "../../components/admin/record-workspace";
import { useRef, useState } from "react";
import { Button } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatusBadge } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel, EmptyState } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { useConnectors } from "../../hooks/use-governance";
import { ConnectorInvokeFlow } from "./connector-invoke-flow";
import type { Connector } from "../../api/types";

type ConnectorActions = { busy: boolean; select: (connector: Connector, trigger: HTMLElement) => void };

function connectorColumns(actions: ConnectorActions): ColumnsType<Connector> {
  return [
    { title: "连接器", dataIndex: "name", render: (name, row) => <div className="af-record-title">
      <strong>{name}</strong><small>{row.description || "未填写说明"}</small></div> },
    { title: "服务地址", dataIndex: "base_url", render: (value) => <p className="af-record-copy">{value}</p> },
    { title: "状态", dataIndex: "enabled", render: (value) => <StatusBadge value={value ? "enabled" : "disabled"} /> },
    { title: "操作", key: "invoke", render: (_, row) => <Button size="small" disabled={actions.busy || !row.enabled}
      onClick={(event) => actions.select(row, event.currentTarget)}>核对并试调用</Button> },
  ];
}

export function ConnectorsPage() {
  const query = useConnectors();
  const [selected, setSelected] = useState<Connector>();
  const [busy, setBusy] = useState(false);
  const trigger = useRef<HTMLElement>();
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["name", "description", "base_url"] });
  const current = query.data?.find((row) => row.name === selected?.name) ?? selected;
  function close() {
    if (busy) return;
    setSelected(undefined); trigger.current?.focus();
  }
  function select(row: Connector, button: HTMLElement) {
    if (busy) return;
    trigger.current = button; setSelected(row);
  }
  return <div className="af-page"><PageHeader title="业务连接器" subtitle="查看外部服务配置，按连接器核对试调用响应。"
    actions={<RefreshButton query={query} />} />
    <ConfigurationWorkspace editor={<WorkspacePanel title="连接器试调用">
      {current ? <ConnectorInvokeFlow key={current.name} connector={current} onBusyChange={setBusy}
        onClose={close} /> : <EmptyState title="选择一个连接器"
        description="核对服务配置后发起试调用，再查看返回内容。" />}
    </WorkspacePanel>}><WorkspacePanel title="已配置的连接器" description="试调用使用空参数；调用行为由连接器实现决定。">
      <FilterBar {...filter} placeholder="搜索名称、地址或说明" count={query.data ? filter.rows.length : undefined} />
      <DataTable query={query} dataSource={filter.rows} columns={connectorColumns({ busy, select })}
        emptyTitle={filter.filtered ? "没有匹配的连接器" : "尚未配置业务连接器"} emptyDescription="配置外部服务后，可在这里检查状态与响应。" />
    </WorkspacePanel></ConfigurationWorkspace>
  </div>;
}
