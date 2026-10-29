import { useCallback, useRef, useState } from "react";
import { Button, Card, InputNumber, Select, Space, Table, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { mall, money, write } from "./client";
import { Feedback, useLoad, type Page } from "./shared";

type Item = { sku_id: string; qty: number; title: string };
type Quote = { checkout_token: string; total_cents: number; currency: string };
type Address = { id: string; name: string; address: string };
type CartQuery = { data?: Page<Item>; reload: () => Promise<void> };
const CHECKOUT_MARGIN = 16;

function useCartActions(query: CartQuery) {
  const orderKey = useRef(crypto.randomUUID());
  const [address, setAddress] = useState("");
  const [quote, setQuote] = useState<Quote>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  async function checkout(place: boolean) {
    setBusy(true); setError("");
    try {
      const body = { items: query.data?.items.map(({ sku_id, qty }) => ({ sku_id, qty })), address_id: address || null };
      if (!place) {
        setQuote(await write<Quote>("/order/checkout", body));
        orderKey.current = crypto.randomUUID();
      }
      else {
        const order = await write<{ id: string }>("/order/orders", { ...body, checkout_token: quote?.checkout_token }, { key: orderKey.current });
        navigate(`/shop/orders/${order.id}`);
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "结算失败"); }
    finally { setBusy(false); }
  }
  async function update(item: Item, qty: number) {
    try {
      const path = "/order/cart/items" + (qty ? "" : "/" + item.sku_id);
      await write(path, qty ? { sku_id: item.sku_id, qty } : {}, { method: qty ? "PUT" : "DELETE" });
      setQuote(undefined); await query.reload(); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "修改购物车失败"); }
  }
  function choose(value?: string) { setAddress(value ?? ""); setQuote(undefined); }
  return { address, quote, error, busy, checkout, update, choose };
}

export function Cart() {
  const query = useLoad(useCallback(() => mall<Page<Item>>("/order/cart"), []));
  const addresses = useLoad(useCallback(() => mall<Page<Address>>("/account/addresses"), []));
  const actions = useCartActions(query);
  return <Card title="购物车与结算"><Feedback {...query} /><Feedback error={actions.error || addresses.error} />
    <Table rowKey="sku_id" dataSource={query.data?.items} pagination={false} columns={[
      { title: "商品", dataIndex: "title" },
      { title: "数量", render: (_, item: Item) => <InputNumber min={1} value={item.qty}
        onChange={(value) => { if (value) void actions.update(item, value); }} /> },
      { title: "操作", render: (_, item: Item) => <Button onClick={() => actions.update(item, 0)}>移除</Button> },
    ]} />
    <Space direction="vertical" style={{ marginTop: CHECKOUT_MARGIN }}>
      <Select placeholder="选择收货地址" value={actions.address || undefined} allowClear
        options={addresses.data?.items.map((row) => ({ value: row.id, label: `${row.name} · ${row.address}` }))}
        onChange={actions.choose} style={{ minWidth: "20em" }} />
      <Button disabled={!query.data?.items.length} loading={actions.busy} onClick={() => actions.checkout(false)}>核对金额</Button>
      {actions.quote && <><Typography.Text>应付：{money(actions.quote.total_cents, actions.quote.currency)}</Typography.Text>
        <Button type="primary" loading={actions.busy} onClick={() => actions.checkout(true)}>确认下单</Button></>}
    </Space>
  </Card>;
}
