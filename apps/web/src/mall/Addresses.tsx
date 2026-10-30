import { useCallback, useState } from "react";
import { Button, List, Popconfirm, Tag } from "antd";
import { mall, write } from "./client";
import { ActionForm, Feedback, useLoad, type Page, type Row } from "./shared";

type Address = { id: string; name: string; phone: string; address: string; is_default: boolean; version: number };
const FIELDS = [{ name: "name", label: "收货人" }, { name: "phone", label: "手机号" },
  { name: "address", label: "详细地址" }];

export function Addresses() {
  const [cursor, setCursor] = useState("");
  const [editing, setEditing] = useState<Address>();
  const [error, setError] = useState("");
  const loader = useCallback(() => mall<Page<Address>>(`/account/addresses?cursor=${encodeURIComponent(cursor)}`), [cursor]);
  const query = useLoad(loader);
  async function save(values: Row) {
    const path = "/account/addresses" + (editing ? "/" + editing.id : "");
    const body = editing ? { ...values, expected_version: editing.version, is_default: editing.is_default } : values;
    await write(path, body, { method: editing ? "PATCH" : "POST" });
    setEditing(undefined); await query.reload();
  }
  async function act(row: Address, remove = false) {
    const { id, version, ...fields } = row;
    const body = remove ? { expected_version: version } : { ...fields, is_default: true, expected_version: version };
    try { await write("/account/addresses/" + id, body, { method: remove ? "DELETE" : "PATCH" }); await query.reload(); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "地址操作失败"); }
  }
  return <><Feedback error={error || query.error} loading={query.loading} />
    <List className="af-address-list" dataSource={query.data?.items} locale={{ emptyText: "暂无收货地址，请添加一条。" }} renderItem={(row) => <List.Item>
      <div className="af-address-identity"><strong>{row.name} {row.is_default && <Tag>默认</Tag>}</strong>
        <p>{row.phone}</p><p>{row.address}</p></div><div className="af-address-actions">
        <Button onClick={() => setEditing(row)}>编辑</Button>
        <Button disabled={row.is_default} onClick={() => act(row)}>设为默认</Button>
        <Popconfirm title="删除此收货地址？" onConfirm={() => act(row, true)}><Button danger>删除</Button></Popconfirm>
      </div></List.Item>} />
    {query.data?.next_cursor && <Button onClick={() => setCursor(query.data!.next_cursor!)}>下一页</Button>}
    <section className="af-address-form"><h3>{editing ? "编辑地址" : "添加收货地址"}</h3>
    <ActionForm key={editing ? editing.id + editing.version : "new"} label={editing ? "保存地址" : "添加地址"}
      initial={editing ? { name: editing.name, phone: editing.phone, address: editing.address } : undefined} fields={FIELDS} submit={save} />
    {editing && <Button onClick={() => setEditing(undefined)}>取消编辑</Button>}</section>
  </>;
}
