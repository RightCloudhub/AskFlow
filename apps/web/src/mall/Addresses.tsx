import { useCallback, useState } from "react";
import { Button, List, Modal, Popconfirm, Tag } from "antd";
import { mall, write } from "./client";
import { ActionForm, useLoad, type Field, type Page, type Row } from "./shared";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";

type Address = { id: string; name: string; phone: string; address: string; is_default: boolean; version: number };
const FIELDS: Field[] = [
  { name: "name", label: "收货人", autoComplete: "shipping name", step: "联系信息" },
  { name: "phone", label: "联系电话", inputMode: "tel", autoComplete: "shipping tel", step: "联系信息" },
  { name: "address", label: "详细地址", kind: "textarea", autoComplete: "shipping street-address", step: "配送地址", hint: "请填写省市区、街道与门牌号，方便配送。" },
  { name: "is_default", label: "设为默认收货地址", kind: "boolean", step: "配送地址" },
];

export function Addresses() {
  const paging = useCursor();
  const [editing, setEditing] = useState<Address>();
  const [open, setOpen] = useState(false);
  const feedback = useActionFeedback();
  const loader = useCallback(() => mall<Page<Address>>(`/account/addresses?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]);
  const query = useLoad(loader);
  async function save(values: Row) {
    const path = "/account/addresses" + (editing ? "/" + editing.id : "");
    const body = editing ? { ...values, expected_version: editing.version } : values;
    await write(path, body, { method: editing ? "PATCH" : "POST" });
    setOpen(false); setEditing(undefined); await query.reload(); feedback.succeed("收货地址已保存。");
  }
  async function act(row: Address, remove = false) {
    const { id, version, ...fields } = row;
    const body = remove ? { expected_version: version } : { ...fields, is_default: true, expected_version: version };
    await feedback.run(async () => {
      await write("/account/addresses/" + id, body, { method: remove ? "DELETE" : "PATCH" }); await query.reload();
    }, remove ? "收货地址已删除。" : "默认地址已更新。");
  }
  return <><div className="af-address-toolbar"><Button type="primary" disabled={feedback.busy}
    onClick={() => { setEditing(undefined); setOpen(true); }}>添加收货地址</Button><QueryRefresh query={query} /></div>
    <ActionFeedback state={feedback} /><MallQuery query={query}>
      <List className="af-address-list" dataSource={query.data?.items} locale={{ emptyText: "还没有收货地址，添加后可用于订单配送。" }} renderItem={(row) => <List.Item>
        <div className="af-address-identity"><strong>{row.name} {row.is_default && <Tag>默认地址</Tag>}</strong>
          <p>{row.phone}</p><p>{row.address}</p></div><div className="af-address-actions">
          <Button type="text" disabled={feedback.busy} onClick={() => { setEditing(row); setOpen(true); }}>编辑</Button>
          {!row.is_default && <Button type="text" disabled={feedback.busy} onClick={() => void act(row)}>设为默认</Button>}
          <Popconfirm title="删除此收货地址？" description="删除后，该地址将不再出现在结算选项中。" okText="删除地址" cancelText="保留"
            onConfirm={() => act(row, true)}><Button type="text" danger disabled={feedback.busy}>删除</Button></Popconfirm>
        </div></List.Item>} />
    </MallQuery><CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
    <Modal title={editing ? "编辑收货地址" : "添加收货地址"} open={open} footer={null} destroyOnHidden onCancel={() => setOpen(false)}>
      <ActionForm key={editing ? `${editing.id}:${editing.version}` : "new"} label="保存地址" fields={FIELDS} submit={save}
        initial={editing ?? { is_default: false }} />
    </Modal>
  </>;
}
