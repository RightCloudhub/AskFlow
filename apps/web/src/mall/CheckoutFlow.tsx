import { useState } from "react";
import { Button, InputNumber, Select } from "antd";
import { Link } from "react-router-dom";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionFeedback } from "../components/common/action-feedback";
import { money } from "./client";
import type { CartItem, useCartActions } from "./cart-state";

export type CheckoutAddress = { id: string; name: string; address: string };
type CartState = ReturnType<typeof useCartActions>;
type CheckoutProps = { actions: CartState; items: CartItem[]; addresses: CheckoutAddress[]; addressesLoading: boolean; blocked: boolean };
const TITLES = ["确认商品", "收货地址", "核对金额"];
const REVIEW_STEP = TITLES.length - 1;

function CartItems({ items, actions }: { items: CartItem[]; actions: CartState }) {
  return <ul className="af-cart-items">{items.map((item) => <li key={item.sku_id} className="af-cart-item">
    <div className="af-cart-item-identity"><h3>{item.title}</h3><span>商品规格</span></div>
    <div className="af-cart-item-controls">
      <InputNumber aria-label={`${item.title}的数量`} min={1} precision={0} value={item.qty}
        disabled={actions.busy} onChange={(value) => { if (value) void actions.update(item, value); }} />
      <Button type="text" disabled={actions.busy} onClick={() => void actions.update(item, 0)}>移除</Button>
    </div>
  </li>)}</ul>;
}

function AddressChoice({ actions, addresses, addressesLoading }: CheckoutProps) {
  return <div className="af-flow-success"><label className="af-field"><span>收货地址（可选）</span>
    <Select aria-label="收货地址" placeholder="选择收货地址" value={actions.address || undefined} allowClear
      loading={addressesLoading} disabled={actions.busy || addressesLoading} onChange={actions.choose}
      options={addresses.map((row) => ({ value: row.id, label: `${row.name} · ${row.address}` }))} />
  </label><Link to="/shop/account?section=addresses">管理收货地址</Link></div>;
}

function CheckoutReview({ actions, items, addresses }: CheckoutProps) {
  const selected = addresses.find((row) => row.id === actions.address);
  return <div className="af-form-review"><dl>
    <div><dt>本次商品</dt><dd>{items.map((item) => `${item.title} × ${item.qty}`).join("\n")}</dd></div>
    <div><dt>商品总数</dt><dd>{items.reduce((count, item) => count + item.qty, 0)} 件</dd></div>
    <div><dt>收货地址</dt><dd>{selected ? `${selected.name} · ${selected.address}` : "未选择"}</dd></div>
  </dl><div className="af-checkout-total"><span>应付金额</span>
    <strong>{actions.quote ? money(actions.quote.total_cents, actions.quote.currency) : "请重新核对金额"}</strong>
  </div></div>;
}

export function CheckoutFlow(props: CheckoutProps) {
  const [current, setCurrent] = useState(0);
  const { actions, blocked } = props;
  const review = current === REVIEW_STEP;
  function back(index: number) {
    if (actions.busy || index < 0 || index >= current) return;
    actions.clearQuote(); setCurrent(index);
  }
  async function next() {
    if (actions.busy || blocked) return;
    if (current === 0) { setCurrent(1); return; }
    const done = await actions.checkout(review);
    if (done && !review) setCurrent(REVIEW_STEP);
  }
  return <FlowFrame titles={TITLES} current={current} onBack={back} busy={actions.busy}>
    <div hidden={current !== 0}><CartItems items={props.items} actions={actions} /></div>
    <div hidden={current !== 1}><AddressChoice {...props} /></div>
    {review && <CheckoutReview {...props} />}
    <ActionFeedback state={actions.feedback} />
    <div className="af-form-flow-actions">
      {current > 0 && <Button disabled={actions.busy} onClick={() => back(current - 1)}>上一步</Button>}
      <Button type="primary" loading={actions.busy} disabled={blocked || (review && !actions.quote)}
        onClick={() => void next()}>{review ? "确认下单" : current === 0 ? "下一步" : "核对金额"}</Button>
    </div>
  </FlowFrame>;
}
