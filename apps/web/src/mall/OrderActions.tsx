import { useEffect, useState } from "react";
import { Alert, Button, Collapse, Popconfirm, Select } from "antd";
import { Link } from "react-router-dom";
import { useFeatures } from "../plugins/features";
import { money, write } from "./client";
import { type Row } from "./shared";
import { StepUp } from "./Verification";
import { AmountInput } from "./AmountInput";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";

export type Order = { id: string; status: string; total_cents: number; currency: string;
  version: number; refunded_cents: number; refund_reserved_cents?: number; created_at?: string; tracking_number?: string;
  items?: { id: string; title_snapshot: string; price_cents: number; qty: number; total_cents: number }[] };
type Payment = { id: string; status: string; external_cents: number };
type Pending = { kind: string; token: string; key: string; body: Row };
const REFUNDABLE = new Set(["PAID", "SHIPPED", "DELIVERED", "COMPLETED", "PARTIALLY_REFUNDED"]);
const refundableAmount = (order: Order) => Math.max(0, order.total_cents - order.refunded_cents - (order.refund_reserved_cents ?? 0));

function useOrderActions(order: Order, reload: () => Promise<void>) {
  const [stepUp, setStepUp] = useState("");
  const [payment, setPayment] = useState<Payment>();
  const [wallet, setWallet] = useState(0);
  const [refund, setRefund] = useState(refundableAmount(order));
  const [destination, setDestination] = useState("original");
  const [pending, setPending] = useState<Pending>();
  const feedback = useActionFeedback();
  useEffect(() => { setRefund(refundableAmount(order)); setPending(undefined); }, [order.version]);
  async function execute(action: () => Promise<unknown>) {
    await feedback.run(async () => { await action(); await reload(); });
  }
  async function confirm(kind: string) {
    const previous = pending?.kind === kind ? pending : undefined;
    const key = previous?.key ?? crypto.randomUUID();
    const body = previous?.body ?? (kind === "cancel" ? { expected_version: order.version } :
      { amount_cents: refund, destination, reason: "customer_request" });
    const response = await write<{ confirmation_token?: string }>(`/order/orders/${order.id}/${kind}`,
      { ...body, confirmation_token: previous?.token ?? "" }, { key });
    setPending(response.confirmation_token ? { kind, key, body, token: response.confirmation_token } : undefined);
    if (!response.confirmation_token) feedback.succeed(kind === "cancel" ? "订单已取消。" : "退款申请已提交，可在售后记录中跟进。");
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
    pending, setPending, feedback, busy: feedback.busy, execute, confirm, pay, settle };
}

type ActionState = ReturnType<typeof useOrderActions>;
type ActionProps = { order: Order; state: ActionState };

function UnpaidActions({ order, state }: ActionProps) {
  const { enabled } = useFeatures();
  return <div className="af-order-action-group">
    {enabled("mall_wallet") && <label className="af-field"><span>钱包抵扣（{order.currency}）</span><AmountInput label="钱包抵扣金额"
      currency={order.currency} max={order.total_cents} value={state.wallet} disabled={state.busy} onChange={state.setWallet} /></label>}
    {enabled("mall_payment") && <><Collapse items={[{ key: "identity", label: "大额支付身份验证",
      children: <StepUp purpose="payment" onToken={state.setStepUp} /> }]} />
      <Button type="primary" loading={state.busy} onClick={() => state.execute(state.pay)}>支付</Button></>}
    <Button loading={state.busy} onClick={() => state.execute(() => state.confirm("cancel"))}>取消订单</Button>
  </div>;
}

function RefundActions({ order, state }: ActionProps) {
  const { enabled } = useFeatures();
  const available = refundableAmount(order);
  return <div className="af-order-action-group"><label className="af-field"><span>退款金额（{order.currency}）</span><AmountInput label="申请退款金额" min={1}
    currency={order.currency} max={available} value={state.refund} disabled={state.busy || !available} onChange={state.setRefund}
    describedBy="af-refund-limit" /><small id="af-refund-limit">当前可申请 {money(available, order.currency)}</small></label>
    <label className="af-field"><span>退款去向</span><Select aria-label="退款去向" value={state.destination} disabled={state.busy} onChange={state.setDestination} options={[
      { value: "original", label: "原支付方式" },
      ...(enabled("mall_wallet") ? [{ value: "wallet", label: "商城钱包" }] : []),
    ]} /></label>
    <Button loading={state.busy} disabled={!available || state.refund > available || state.refund <= 0}
      onClick={() => state.execute(() => state.confirm("refunds"))}>申请退款</Button></div>;
}

function Confirmation({ order, state }: ActionProps) {
  if (!state.pending) return null;
  const pending = state.pending;
  const label = pending.kind === "cancel" ? "确认取消此订单？" :
    `确认退款 ${money(Number(pending.body.amount_cents), order.currency)} 至${pending.body.destination === "wallet" ? "商城钱包" : "原支付方式"}？`;
  return <div className="af-order-confirmation"><Alert type="warning" showIcon title={label} />
    <div className="af-work-actions"><Button danger loading={state.busy} onClick={() => state.execute(() => state.confirm(pending.kind))}>
      {pending.kind === "cancel" ? "确认取消订单" : "确认申请退款"}</Button>
    <Button disabled={state.busy} onClick={() => state.setPending(undefined)}>返回修改</Button></div></div>;
}

export function OrderActions({ order, reload }: { order: Order; reload: () => Promise<void> }) {
  const { enabled } = useFeatures();
  const state = useOrderActions(order, reload);
  return <div className="af-order-actions"><ActionFeedback state={state.feedback} />
    {!state.pending && order.status === "PENDING_PAYMENT" && <UnpaidActions order={order} state={state} />}
    {Boolean(state.payment?.external_cents) && <div className="af-topup-pending"><Alert type="info" showIcon title="模拟支付" description="当前使用模拟网关，不会扣取真实银行卡资金。" />
      <Button loading={state.busy} onClick={() => state.execute(state.settle)}>模拟完成支付</Button></div>}
    {!state.pending && enabled("mall_payment") && REFUNDABLE.has(order.status) && <RefundActions order={order} state={state} />}
    <Confirmation order={order} state={state} />
    {order.status === "SHIPPED" && <Popconfirm title="已收到并核对商品？" okText="确认收货" cancelText="稍后确认" onConfirm={() => state.execute(() =>
      write(`/order/orders/${order.id}/received`, { expected_version: order.version }))}><Button loading={state.busy}>确认收货</Button></Popconfirm>}
    {enabled("mall_support") && <Link to={`/shop/messages?order_id=${order.id}`}>联系订单客服</Link>}
  </div>;
}
