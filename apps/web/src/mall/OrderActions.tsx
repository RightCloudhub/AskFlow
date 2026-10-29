import { useState } from "react";
import { Button, Collapse, InputNumber, Select, Space, Typography } from "antd";
import { Link } from "react-router-dom";
import { useFeatures } from "../plugins/features";
import { money, write } from "./client";
import { Feedback, type Row } from "./shared";
import { StepUp } from "./Verification";

export type Order = { id: string; status: string; total_cents: number; currency: string;
  version: number; refunded_cents: number };
type Payment = { id: string; status: string; external_cents: number };
type Pending = { kind: string; token: string; key: string; body: Row };
const REFUNDABLE = new Set(["PAID", "SHIPPED", "DELIVERED", "COMPLETED", "PARTIALLY_REFUNDED"]);

function useOrderActions(order: Order, reload: () => Promise<void>) {
  const [stepUp, setStepUp] = useState("");
  const [payment, setPayment] = useState<Payment>();
  const [wallet, setWallet] = useState(0);
  const [refund, setRefund] = useState(order.total_cents - order.refunded_cents);
  const [destination, setDestination] = useState("original");
  const [pending, setPending] = useState<Pending>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function execute(action: () => Promise<unknown>) {
    setBusy(true); setError("");
    try { await action(); await reload(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "操作失败"); }
    finally { setBusy(false); }
  }
  async function confirm(kind: string) {
    const previous = pending?.kind === kind ? pending : undefined;
    const key = previous?.key ?? crypto.randomUUID();
    const body = previous?.body ?? (kind === "cancel" ? { expected_version: order.version } :
      { amount_cents: refund, destination, reason: "customer_request" });
    const response = await write<{ confirmation_token?: string }>(`/order/orders/${order.id}/${kind}`,
      { ...body, confirmation_token: previous?.token ?? "" }, { key });
    setPending(response.confirmation_token ? { kind, key, body, token: response.confirmation_token } : undefined);
  }
  async function pay() {
    setPayment(await write<Payment>("/payment", { order_id: order.id, method: wallet ? "mixed" : "mock",
      wallet_cents: wallet, step_up_token: stepUp }));
  }
  async function settle() {
    if (!payment) return;
    await write(`/payment/${payment.id}/mock`, { status: "succeeded" });
    setPayment(undefined);
  }
  return { stepUp, setStepUp, payment, wallet, setWallet, refund, setRefund, destination, setDestination,
    pending, setPending, error, busy, execute, confirm, pay, settle };
}

type ActionState = ReturnType<typeof useOrderActions>;
type ActionProps = { order: Order; state: ActionState };

function UnpaidActions({ order, state }: ActionProps) {
  const { enabled } = useFeatures();
  return <>
    {enabled("mall_wallet") && <InputNumber aria-label="钱包抵扣（分）" min={0} precision={0}
      max={order.total_cents} value={state.wallet} onChange={(value) => state.setWallet(value ?? 0)} />}
    {enabled("mall_payment") && <><Collapse items={[{ key: "identity", label: "大额支付身份验证",
      children: <StepUp purpose="payment" onToken={state.setStepUp} /> }]} />
      <Button loading={state.busy} onClick={() => state.execute(state.pay)}>支付</Button></>}
    <Button loading={state.busy} onClick={() => state.execute(() => state.confirm("cancel"))}>取消订单</Button>
  </>;
}

function RefundActions({ order, state }: ActionProps) {
  const { enabled } = useFeatures();
  return <><InputNumber aria-label="退款金额（分）" min={1} precision={0}
    max={order.total_cents - order.refunded_cents} value={state.refund} onChange={(value) => state.setRefund(value ?? 1)} />
    <Select aria-label="退款去向" value={state.destination} onChange={state.setDestination} options={[
      { value: "original", label: "原支付方式" },
      ...(enabled("mall_wallet") ? [{ value: "wallet", label: "商城钱包" }] : []),
    ]} />
    <Button loading={state.busy} onClick={() => state.execute(() => state.confirm("refunds"))}>申请退款</Button></>;
}

function Confirmation({ order, state }: ActionProps) {
  if (!state.pending) return null;
  const pending = state.pending;
  const label = pending.kind === "cancel" ? "确认取消此订单？" :
    `确认退款 ${money(Number(pending.body.amount_cents), order.currency)} 至${pending.body.destination === "wallet" ? "商城钱包" : "原支付方式"}？`;
  return <Space direction="vertical"><Typography.Text>{label}</Typography.Text>
    <Button danger loading={state.busy} onClick={() => state.execute(() => state.confirm(pending.kind))}>确认此操作</Button>
    <Button disabled={state.busy} onClick={() => state.setPending(undefined)}>返回修改</Button></Space>;
}

export function OrderActions({ order, reload }: { order: Order; reload: () => Promise<void> }) {
  const { enabled } = useFeatures();
  const state = useOrderActions(order, reload);
  return <Space direction="vertical"><Feedback error={state.error} />
    {order.status === "PENDING_PAYMENT" && <UnpaidActions order={order} state={state} />}
    {Boolean(state.payment?.external_cents) && <Button loading={state.busy}
      onClick={() => state.execute(state.settle)}>模拟支付成功</Button>}
    {enabled("mall_payment") && REFUNDABLE.has(order.status) && <RefundActions order={order} state={state} />}
    <Confirmation order={order} state={state} />
    {order.status === "SHIPPED" && <Button loading={state.busy} onClick={() => state.execute(() =>
      write(`/order/orders/${order.id}/received`, { expected_version: order.version }))}>确认收货</Button>}
    {enabled("mall_support") && <Link to={`/shop/messages?order_id=${order.id}`}>联系订单客服</Link>}
  </Space>;
}
