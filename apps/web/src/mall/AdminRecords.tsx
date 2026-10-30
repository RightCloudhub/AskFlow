import { useCallback, useState } from "react";
import { Drawer, Input, Space, Table, Tabs } from "antd";
import { mall } from "./client";
import { useLoad, type Page, type Row } from "./shared";
import { recordColumns } from "./record-columns";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { FilterBar } from "../components/admin/workspace";
import { useRecordFilter } from "../components/admin/use-record-filter";
import { JsonView } from "../components/common/json";

export function Records({ path }: { path: string }) {
  const paging = useCursor();
  const [selected, setSelected] = useState<Row>();
  const loader = useCallback(() => mall<Page<Row>>(
    "/api/v1/admin/mall" + path + "?cursor=" + encodeURIComponent(paging.cursor)), [path, paging.cursor]);
  const query = useLoad(loader);
  const filter = useRecordFilter({ rows: query.data?.items ?? [], fields: Object.keys(query.data?.items[0] ?? {}) });
  return <div className="af-mall-admin-records"><QueryRefresh query={query} />
    <FilterBar {...filter} count={query.data ? filter.rows.length : undefined} placeholder="搜索本页业务记录" />
    <MallQuery query={query}><Table rowKey={(row: Row) => String(row.id ?? row.key)}
      columns={[...recordColumns(query.data?.items ?? []), { title: "详情", key: "detail", render: (_, row) =>
        <button className="af-record-detail-button" type="button" onClick={() => setSelected(row)}>查看详情</button> }]}
      dataSource={filter.rows} pagination={false} scroll={{ x: "max-content" }}
      locale={{ emptyText: filter.filtered ? "没有匹配的业务记录，请调整关键词。" : "暂无业务记录。" }} /></MallQuery>
    <CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
    <Drawer title="业务记录详情" open={Boolean(selected)} onClose={() => setSelected(undefined)} destroyOnHidden>
      {selected && <JsonView data={selected} title="完整记录" />}
    </Drawer>
  </div>;
}

function Differences() {
  const [runId, setRunId] = useState("");
  return <Space direction="vertical" style={{ width: "100%" }}>
    <Input.Search aria-label="对账批次编号" placeholder="输入对账批次编号" onSearch={(value) => setRunId(value.trim())} />
    {runId ? <Records key={runId} path={`/wallet/reconciliation/${encodeURIComponent(runId)}/diffs`} /> :
      <p className="af-mall-note">输入对账批次编号后，查看该批次需要复核的差异。</p>}
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
