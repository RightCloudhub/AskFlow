import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { write } from "./client";

export type CartItem = { sku_id: string; qty: number; title: string };
type Item = CartItem;
type Quote = { checkout_token: string; total_cents: number; currency: string };
type CartQuery = { data?: { items: Item[] }; reload: () => Promise<void> };

export function useCartActions(query: CartQuery) {
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
    setBusy(true);
    setQuote(undefined);
    try {
      const path = "/order/cart/items" + (qty ? "" : "/" + item.sku_id);
      await write(path, qty ? { sku_id: item.sku_id, qty } : {}, { method: qty ? "PUT" : "DELETE" });
      setQuote(undefined); await query.reload(); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "修改购物车失败"); }
    finally { setBusy(false); }
  }
  function choose(value?: string) { setAddress(value ?? ""); setQuote(undefined); }
  return { address, quote, error, busy, checkout, update, choose };
}
