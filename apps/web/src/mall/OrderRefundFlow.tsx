import { useId, useState } from "react";
import { Alert, Button, Input, Select } from "antd";
import { Link } from "react-router-dom";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionFeedback } from "../components/common/action-feedback";
import { useFeatures } from "../plugins/features";
import { AmountInput } from "./AmountInput";
import { money } from "./client";
import { useOrderCommand } from "./order-command";
import { refundableAmount, REFUNDABLE_STATUSES, type OrderFlowProps } from "./order-types";

const TITLES = ["退款金额", "去向与原因", "确认申请"];
const REVIEW_STEP = TITLES.length - 1;
const MAX_REASON_LENGTH = 128;
const REASON_ROWS = 3;
type Destination = "original" | "wallet";

function useRefundFlow(props: OrderFlowProps, walletEnabled: boolean) {
  const [current, setCurrent] = useState(0);
  const [amount, setAmount] = useState(refundableAmount(props.order));
  const [destinationValue, setDestination] = useState<Destination>("original");
  const [reason, setReason] = useState("");
  const command = useOrderCommand({ ...props, kind: "refunds" });
  const available = refundableAmount(props.order);
  const destination = walletEnabled ? destinationValue : "original";
  function validateAmount() {
    if (!REFUNDABLE_STATUSES.has(props.order.status)) throw new Error("当前订单状态不支持退款，请返回订单服务查看。");
    if (!Number.isSafeInteger(amount) || amount <= 0 || amount > available) throw new Error("请填写可申请范围内的退款金额。");
  }
  function body() {
    validateAmount();
    const trimmed = reason.trim();
    if (!trimmed || trimmed.length > MAX_REASON_LENGTH) throw new Error(`请填写退款原因，最多 ${MAX_REASON_LENGTH} 个字。`);
    return { amount_cents: amount, destination, reason: trimmed };
  }
  function back(index: number) {
    if (command.locked || command.complete || index < 0 || index >= current) return;
    command.invalidate(); setCurrent(index);
  }
  async function next() {
    if (command.locked || command.complete) return;
    if (current === 0) {
      await command.feedback.run(async () => { validateAmount(); setCurrent(1); });
      return;
    }
    if (await command.prepare(body)) setCurrent(REVIEW_STEP);
  }
  return { current, amount, setAmount, destination, setDestination, reason, setReason, available, command, back, next };
}

type RefundState = ReturnType<typeof useRefundFlow>;
type RefundStepProps = { state: RefundState; order: OrderFlowProps["order"] };

function RefundAmount({ state, order }: RefundStepProps) {
  const hintId = useId();
  return <label className="af-field"><span>申请退款金额（{order.currency}）</span>
    <AmountInput label="申请退款金额" currency={order.currency} min={1} max={state.available}
      value={state.amount} disabled={state.command.busy || !state.available} onChange={state.setAmount} describedBy={hintId} />
    <small id={hintId}>当前可申请 {money(state.available, order.currency)}，已扣除已退款和处理中的申请。</small>
  </label>;
}

function RefundDetails({ state, walletEnabled }: { state: RefundState; walletEnabled: boolean }) {
  const reasonId = useId();
  return <div className="af-flow-success">
    <label className="af-field"><span>退款去向</span>
      <Select aria-label="退款去向" value={state.destination} disabled={state.command.busy} onChange={state.setDestination}
        options={[{ value: "original", label: "原支付方式" }, ...(walletEnabled ? [{ value: "wallet", label: "商城钱包" }] : [])]} />
    </label>
    <div className="af-field"><label htmlFor={reasonId}>退款原因</label>
      <Input.TextArea id={reasonId} value={state.reason} maxLength={MAX_REASON_LENGTH} rows={REASON_ROWS} showCount
        disabled={state.command.busy} onChange={(event) => state.setReason(event.target.value)} placeholder="请说明申请退款的原因" />
    </div>
  </div>;
}

function RefundReview({ state, order }: RefundStepProps) {
  const pending = state.command.pending;
  if (!pending) return <Alert type="warning" showIcon title="确认信息已失效"
    description="请返回修改，或重新核对当前金额与退款去向。" />;
  return <div className="af-flow-success">
    <div className="af-form-review"><dl>
      <div><dt>申请金额</dt><dd>{money(Number(pending.body.amount_cents), order.currency)}</dd></div>
      <div><dt>退款去向</dt><dd>{pending.body.destination === "wallet" ? "商城钱包" : "原支付方式"}</dd></div>
      <div><dt>退款原因</dt><dd>{String(pending.body.reason)}</dd></div>
    </dl></div>
    <Alert type="info" showIcon title={pending.requires_human_approval ? "本次申请需要人工审核" : "提交后可在售后记录跟进"}
      description="退款金额与到账进度以实际处理结果为准。" />
  </div>;
}

function RefundNavigation({ state, onExit }: { state: RefundState; onExit: () => void }) {
  const { command } = state;
  const review = state.current === REVIEW_STEP;
  return <div className="af-form-flow-actions">
    {state.current > 0 && <Button disabled={command.locked} onClick={() => state.back(state.current - 1)}>上一步</Button>}
    <Button disabled={command.locked} onClick={onExit}>返回订单服务</Button>
    {review && command.pending
      ? <Button type="primary" loading={command.busy} onClick={() => void command.submit()}>
        {command.awaitingResult ? "重试并获取结果" : "确认申请退款"}</Button>
      : <Button type="primary" loading={command.busy} disabled={!state.available}
        onClick={() => void state.next()}>{review ? "重新核对" : "下一步"}</Button>}
  </div>;
}

export function OrderRefundFlow(props: OrderFlowProps) {
  const { enabled } = useFeatures();
  const walletEnabled = enabled("mall_wallet");
  const state = useRefundFlow(props, walletEnabled);
  const { command } = state;
  return <FlowFrame titles={TITLES} current={state.current} title={command.complete ? "申请已提交" : undefined}
    onBack={state.back} busy={command.busy} backDisabled={command.complete || command.awaitingResult} focusOnMount>
    {command.complete ? <div className="af-flow-success">
      <Alert type="success" showIcon title="退款申请已提交" description="可在售后记录中查看处理进度。" />
      <Link to="/shop/refunds">查看售后记录</Link>
      <Button disabled={command.busy} onClick={props.onExit}>返回订单服务</Button>
    </div> : <>
      <div hidden={state.current !== 0}><RefundAmount state={state} order={props.order} /></div>
      <div hidden={state.current !== 1}><RefundDetails state={state} walletEnabled={walletEnabled} /></div>
      {state.current === REVIEW_STEP && <RefundReview state={state} order={props.order} />}
      <RefundNavigation state={state} onExit={props.onExit} />
    </>}
    {command.awaitingResult && !command.busy && <p className="af-mall-note">尚未收到处理结果。重试会继续原申请，获取结果后再修改。</p>}
    <ActionFeedback state={command.feedback} />
  </FlowFrame>;
}
