import { Alert, Button, Typography } from "antd";
import { Link } from "react-router-dom";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionFeedback } from "../components/common/action-feedback";
import { useFeatures } from "../plugins/features";
import { AmountInput } from "./AmountInput";
import { StepUp } from "./StepUp";
import { money } from "./client";
import { useOrderPaymentFlow, type OrderPayment } from "./order-payment-state";
import type { OrderFlowProps } from "./order-types";
import { MallStatus } from "./presentation";

type PaymentState = ReturnType<typeof useOrderPaymentFlow>;
type StepProps = { state: PaymentState; order: OrderFlowProps["order"] };

function PaymentAmounts({ payment }: { payment: Pick<OrderPayment, "amount_cents" | "wallet_cents" | "external_cents" | "currency"> }) {
  return <div className="af-form-review"><dl>
    <div><dt>订单金额</dt><dd>{money(payment.amount_cents, payment.currency)}</dd></div>
    <div><dt>钱包抵扣</dt><dd>{money(payment.wallet_cents, payment.currency)}</dd></div>
    <div><dt>模拟网关支付</dt><dd>{money(payment.external_cents, payment.currency)}</dd></div>
  </dl></div>;
}

function PaymentMethod({ state, order, walletEnabled }: StepProps & { walletEnabled: boolean }) {
  return <div className="af-flow-success">
    <div className="af-mall-key-value"><span>订单金额</span><strong>{money(order.total_cents, order.currency)}</strong></div>
    {walletEnabled && <label className="af-field"><span>钱包抵扣金额（{order.currency}）</span>
      <AmountInput label="钱包抵扣金额" currency={order.currency} value={state.wallet} max={order.total_cents}
        disabled={state.busy} onChange={state.setWallet} />
      <small>可填写零，剩余金额通过模拟网关支付。</small>
    </label>}
    {state.wallet < order.total_cents && <Alert type="info" showIcon title="模拟支付"
      description="剩余金额使用模拟网关，不会扣取真实银行卡资金；钱包抵扣会影响商城钱包余额。" />}
  </div>;
}

function PaymentReview({ state, order }: StepProps) {
  return <div className="af-flow-success">
    <PaymentAmounts payment={{ amount_cents: order.total_cents, wallet_cents: state.wallet,
      external_cents: order.total_cents - state.wallet, currency: order.currency }} />
    {!state.reviewValid && <Alert type="warning" showIcon title="订单信息已更新，请返回上一步重新核对。" />}
    <p className="af-mall-note">确认后创建或继续该订单的支付单。全额使用钱包时，将直接扣款并完成支付。</p>
  </div>;
}

function PaymentOutcome({ state, onExit }: { state: PaymentState; onExit: () => void }) {
  const payment = state.payment;
  if (!payment) return null;
  const pending = payment.status === "pending";
  const canSettle = pending && payment.external_cents > 0 && !state.settlementSent;
  return <div className="af-flow-success">
    <MallStatus value={payment.status} />
    <PaymentAmounts payment={payment} />
    <Typography.Paragraph type="secondary" copyable={{ text: payment.id }}>支付单 {payment.id}</Typography.Paragraph>
    {canSettle && <Alert type="info" showIcon title="等待模拟支付" description="点击下方按钮完成模拟网关付款，不会扣取真实银行卡资金。" />}
    {pending && state.settlementSent && <p className="af-mall-note">模拟结果已提交，请刷新查看最终支付状态。</p>}
    <div className="af-form-flow-actions">
      {canSettle && <Button type="primary" loading={state.busy} onClick={() => void state.settle()}>模拟完成支付</Button>}
      <Button loading={state.busy} onClick={() => void state.refresh()}>刷新支付状态</Button>
      {!pending && <Button disabled={state.busy} onClick={onExit}>返回订单服务</Button>}
    </div>
    <Link to={`/shop/payment-result?payment_id=${encodeURIComponent(payment.id)}`}>查看支付详情</Link>
  </div>;
}

function PaymentNavigation({ state, onExit }: { state: PaymentState; onExit: () => void }) {
  const review = state.stage === "review";
  const identityMissing = state.stage === "identity" && !state.token;
  const disabled = !state.payable || !state.validAmount || identityMissing || (review && !state.reviewValid);
  return <div className="af-form-flow-actions">
    {state.current > 0 && <Button disabled={state.busy} onClick={() => state.back(state.current - 1)}>上一步</Button>}
    <Button disabled={state.busy} onClick={onExit}>返回订单服务</Button>
    <Button type="primary" loading={state.busy} disabled={disabled}
      onClick={() => review ? void state.start() : state.next()}>{review ? "确认支付" : "下一步"}</Button>
  </div>;
}

export function OrderPaymentFlow(props: OrderFlowProps) {
  const { enabled } = useFeatures();
  const walletEnabled = enabled("mall_wallet");
  const state = useOrderPaymentFlow({ ...props, walletEnabled });
  return <FlowFrame titles={state.titles} current={state.current} onBack={state.back} busy={state.busy} backDisabled={Boolean(state.payment)} focusOnMount>
    {state.stage === "amount" && <PaymentMethod state={state} order={props.order} walletEnabled={walletEnabled} />}
    <div hidden={state.stage !== "identity"}>
      {state.identityRequired && <StepUp key={state.identityRevision} purpose="payment" onToken={state.setToken} onBusyChange={state.setIdentityBusy} />}
    </div>
    {state.stage === "review" && <PaymentReview state={state} order={props.order} />}
    {state.stage === "result" && <PaymentOutcome state={state} onExit={props.onExit} />}
    {!state.payment && !state.payable && <Alert type="warning" showIcon title="订单状态已变化，请返回订单服务查看。" />}
    <ActionFeedback state={state.feedback} />
    {!state.payment && <PaymentNavigation state={state} onExit={props.onExit} />}
  </FlowFrame>;
}
