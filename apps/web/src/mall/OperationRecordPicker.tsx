import { useCallback, useState } from "react";
import { Button, Select } from "antd";
import { mall } from "./client";
import { Feedback, useLoad, type Page, type Row } from "./shared";
import { recordLabel, type OperationResource } from "./operation-records";

type Props = { resource: OperationResource; selected?: Row; onSelect: (row: Row | undefined) => void; disabled?: boolean };

export function OperationRecordPicker({ resource, selected, onSelect, disabled }: Props) {
  const [cursor, setCursor] = useState("");
  const [previous, setPrevious] = useState<Row[]>([]);
  const query = useLoad(useCallback(() => mall<Page<Row>>(`/api/v1/admin/mall${resource.path}?cursor=${encodeURIComponent(cursor)}`), [resource.path, cursor]));
  const rows = [...previous, ...query.data?.items ?? []].filter((row) => !resource.excludeBuiltin || !row.builtin);
  const unique = Array.from(new Map(rows.map((row) => [String(row[resource.valueKey ?? "id"]), row])).values());
  function select(value: string) {
    const row = unique.find((item) => String(item[resource.valueKey ?? "id"]) === value);
    if (row) onSelect(row);
  }
  return <div className="af-operation-picker"><label className="af-field"><span>{`选择${resource.label}`}</span>
    <Select aria-label={`选择${resource.label}`} showSearch optionFilterProp="label" loading={query.loading} disabled={disabled}
      value={selected ? String(selected[resource.valueKey ?? "id"]) : undefined} onChange={select}
      placeholder={`搜索并选择${resource.label}`} notFoundContent={query.loading ? "正在读取…" : "暂无匹配记录"}
      options={unique.map((row) => ({ value: String(row[resource.valueKey ?? "id"]),
        label: recordLabel(row), title: String(row.id ?? row.key) }))} />
  </label><Feedback {...query} />
    <Button type="text" disabled={query.loading || disabled} onClick={() => {
      onSelect(undefined); setPrevious([]); setCursor(""); if (!cursor) void query.reload();
    }}>刷新记录</Button>
    {query.data?.next_cursor && <Button type="text" disabled={query.loading || disabled} onClick={() => {
      setPrevious(unique); setCursor(query.data?.next_cursor ?? "");
    }}>加载更多{resource.label}</Button>}
  </div>;
}
