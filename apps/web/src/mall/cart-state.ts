import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { write } from "./client";
import { useActionFeedback } from "../components/common/action-feedback";

export type CartItem = { sku_id: string; qty: number; title: string };
type Quote = { checkout_token: string; total_cents: number; currency: string };
type CartQuery = { data?: { items: CartItem[] }; reload: () => Promise<void> };

export function useCartActions(query: CartQuery) {
  const orderKey = useRef(crypto.randomUUID());
  const [address, setAddress] = useState("");
  const [quote, setQuote] = useState<Quote & { signature: string }>();
  const feedback = useActionFeedback();
  const navigate = useNavigate();
  function body() {
    return { items: query.data?.items.map(({ sku_id, qty }) => ({ sku_id, qty })), address_id: address || null };
  }
  async function quoteOrder() {
    setQuote(undefined);
    const payload = body();
    const result = await write<Quote>("/order/checkout", payload);
    setQuote({ ...result, signature: JSON.stringify(payload) });
    orderKey.current = crypto.randomUUID();
  }
  async function placeOrder() {
    const payload = body();
    if (!quote || quote.signature !== JSON.stringify(payload)) {
      setQuote(undefined);
      throw new Error("结算信息已变化，请返回上一步重新核对金额。");
    }
    const order = await write<{ id: string }>("/order/orders", {
      ...payload, checkout_token: quote.checkout_token,
    }, { key: orderKey.current });
    navigate(`/shop/orders/${order.id}`);
  }
  async function update(item: CartItem, qty: number) {
    return feedback.run(async () => {
      setQuote(undefined);
      const path = "/order/cart/items" + (qty ? "" : "/" + item.sku_id);
      await write(path, qty ? { sku_id: item.sku_id, qty } : {}, { method: qty ? "PUT" : "DELETE" });
      await query.reload();
    });
  }
  function choose(value?: string) {
    if (feedback.busy) return;
    setAddress(value ?? ""); setQuote(undefined); feedback.clear();
  }
  function clearQuote() { if (!feedback.busy) { setQuote(undefined); feedback.clear(); } }
  const currentQuote = quote?.signature === JSON.stringify(body()) ? quote : undefined;
  return { address, quote: currentQuote, feedback, busy: feedback.busy, update, choose, clearQuote,
    checkout: (place: boolean) => feedback.run(place ? placeOrder : quoteOrder) };
}
