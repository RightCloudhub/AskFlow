import { useCallback, useState } from "react";
import { Button, Input, Space, Table, Tabs } from "antd";
import { mall } from "./client";
import { Feedback, useLoad, type Page, type Row } from "./shared";

export function Records({ path }: { path: string }) {
  const [cursor, setCursor] = useState("");
  const loader = useCallback(() => mall<Page<Row>>(
    "/api/v1/admin/mall" + path + "?cursor=" + encodeURIComponent(cursor)), [path, cursor]);
  const query = useLoad(loader);
  const columns = Object.keys(query.data?.items[0] ?? {}).map((key) => ({
    title: key, key, dataIndex: key,
    render: (value: unknown) => typeof value === "object" ? JSON.stringify(value) : String(value ?? ""),
  }));
  return <Space direction="vertical" style={{ width: "100%" }}><Feedback {...query} />
    <Table rowKey={(row: Row) => String(row.id ?? row.key)} columns={columns}
      dataSource={query.data?.items} pagination={false} scroll={{ x: true }} />
    <Button onClick={() => { setCursor(""); void query.reload(); }}>刷新</Button>
    {query.data?.next_cursor && <Button onClick={() => setCursor(query.data!.next_cursor!)}>下一页</Button>}
  </Space>;
}

function Differences() {
  const [runId, setRunId] = useState("");
  return <Space direction="vertical" style={{ width: "100%" }}>
    <Input.Search aria-label="对账批次编号" placeholder="输入对账批次编号" onSearch={setRunId} />
    {runId && <Records key={runId} path={`/wallet/reconciliation/${encodeURIComponent(runId)}/diffs`} />}
  </Space>;
}

export function FinanceRecords({ permissions }: { permissions: string[] }) {
  const items = [
    { key: "accounts", label: "账户余额", children: <Records path="/wallet/accounts" /> },
    { key: "adjustments", label: "调账申请", children: <Records path="/wallet/adjustments" /> },
    { key: "reversals", label: "冲正申请", children: <Records path="/wallet/reversals" /> },
  ];
  if (permissions.includes("finance:reconcile")) items.push(
    { key: "runs", label: "对账批次", children: <Records path="/wallet/reconciliation" /> },
    { key: "differences", label: "对账差异", children: <Differences /> },
  );
  return <Tabs items={items} />;
}
