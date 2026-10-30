import { useCallback } from "react";
import { Link } from "react-router-dom";
import { mall } from "./client";
import { Feedback, useLoad, type Page } from "./shared";
import { MallEmpty, MallPage, MallPanel } from "./presentation";
import { useCartActions, type CartItem } from "./cart-state";
import { MallQuery } from "./query-view";
import { CheckoutFlow, type CheckoutAddress } from "./CheckoutFlow";

export function Cart() {
  const query = useLoad(useCallback(() => mall<Page<CartItem>>("/order/cart"), []));
  const addresses = useLoad(useCallback(() => mall<Page<CheckoutAddress>>("/account/addresses"), []));
  const actions = useCartActions(query);
  const items = query.data?.items ?? [];
  return <MallPage title="购物车与结算" description="确认商品、数量与收货地址，再核对应付金额。"
    actions={<Link to="/shop">继续选购</Link>}>
    <Feedback error={addresses.error} reload={addresses.reload} />
    <MallQuery query={query}>{!items.length ? <MallEmpty title="购物车里还没有商品">
      <Link to="/shop">前往商品目录</Link>
    </MallEmpty> : <MallPanel title="确认本次订单" className="af-checkout-flow">
      <CheckoutFlow actions={actions} items={items} addresses={addresses.data?.items ?? []}
        addressesLoading={addresses.loading} blocked={query.loading || Boolean(query.error) || addresses.loading || Boolean(addresses.error)} />
    </MallPanel>}</MallQuery>
  </MallPage>;
}
