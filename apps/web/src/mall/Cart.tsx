import { useCallback } from "react";
import { Button, InputNumber, Select } from "antd";
import { Link } from "react-router-dom";
import { mall, money } from "./client";
import { Feedback, useLoad, type Page } from "./shared";
import { MallEmpty, MallPage, MallPanel } from "./presentation";
import { useCartActions, type CartItem } from "./cart-state";

type Address = { id: string; name: string; address: string };
type CartState = ReturnType<typeof useCartActions>;

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

function CheckoutSummary({ actions, addresses, count }: { actions: CartState; addresses: Address[]; count: number }) {
  return <MallPanel title="结算摘要" className="af-checkout-summary">
    <div className="af-mall-key-value"><span>商品数量</span><strong>{count} 件</strong></div>
    <label className="af-field"><span>收货地址</span>
      <Select aria-label="收货地址" placeholder="选择收货地址" value={actions.address || undefined} allowClear disabled={actions.busy}
        options={addresses.map((row) => ({ value: row.id, label: `${row.name} · ${row.address}` }))} onChange={actions.choose} />
    </label>
    <Link className="af-mall-text-link" to="/shop/account">管理收货地址</Link>
    {actions.quote ? <><div className="af-checkout-total"><span>应付金额</span>
      <strong>{money(actions.quote.total_cents, actions.quote.currency)}</strong></div>
      <Button type="primary" block loading={actions.busy} onClick={() => void actions.checkout(true)}>确认下单</Button>
      <Button block disabled={actions.busy} onClick={() => void actions.checkout(false)}>重新核对金额</Button>
    </> : <><p className="af-mall-note">选择商品与收货地址后，核对本次订单的应付金额。</p>
      <Button type="primary" block disabled={!count} loading={actions.busy} onClick={() => void actions.checkout(false)}>核对金额</Button></>}
  </MallPanel>;
}

export function Cart() {
  const query = useLoad(useCallback(() => mall<Page<CartItem>>("/order/cart"), []));
  const addresses = useLoad(useCallback(() => mall<Page<Address>>("/account/addresses"), []));
  const actions = useCartActions(query);
  const items = query.data?.items ?? [];
  const count = items.reduce((total, item) => total + item.qty, 0);
  return <MallPage title="购物车与结算" description="确认商品、数量与收货地址，再核对应付金额。"
    actions={<Link to="/shop">继续选购</Link>}>
    <Feedback {...query} /><Feedback error={actions.error || addresses.error} />
    {!query.loading && !query.error && !items.length ? <MallEmpty title="购物车里还没有商品">
      <Link to="/shop">前往商品目录</Link>
    </MallEmpty> : <div className="af-mall-columns">
      <MallPanel title="已选商品" description={`共 ${items.length} 种商品`}><CartItems items={items} actions={actions} /></MallPanel>
      <CheckoutSummary actions={actions} addresses={addresses.data?.items ?? []} count={count} />
    </div>}
  </MallPage>;
}
