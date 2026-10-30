import { useId, useRef, useState } from "react";
import { Alert, Button, Form, Typography } from "antd";
import { Link } from "react-router-dom";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { money, write } from "./client";
import { majorToMinor } from "./money-values";
import { MINOR_UNITS } from "./form-fields";
import { FormFields } from "./form-steps";

type TopUpProps = { reload: () => Promise<void>; currency: string };
type Payment = { id: string; amount: number };
const TITLES = ["充值金额", "核对充值", "完成支付"];
const PAYMENT_STEP = TITLES.length - 1;

function useTopUpState() {
  const [form] = Form.useForm();
  const [current, setCurrent] = useState(0);
  const [payment, setPayment] = useState<Payment>();
  const [complete, setComplete] = useState(false);
  const [amount, setAmount] = useState(0);
  const [validating, setValidating] = useState(false);
  const locked = useRef(false);
  const requestKey = useRef(crypto.randomUUID());
  const feedback = useActionFeedback();
  const busy = validating || feedback.busy;
  function changed() { requestKey.current = crypto.randomUUID(); feedback.clear(); }
  function back(index: number) { if (!busy && !payment && index < current) { setCurrent(index); feedback.clear(); } }
  return { form, current, payment, complete, amount, locked, requestKey, feedback, busy, changed, back,
    setCurrent, setPayment, setComplete, setValidating, setAmount };
}

function useTopUpFlow({ reload }: TopUpProps) {
  const state = useTopUpState();
  async function advance() {
    if (state.locked.current || state.busy || state.payment) return;
    state.locked.current = true; state.setValidating(true);
    try {
      try { await state.form.validateFields(); }
      catch { state.setCurrent(0); return; }
      await state.feedback.run(async () => {
        const amount = majorToMinor(Number(state.form.getFieldValue("amount_cents")));
        if (amount <= 0) throw new Error("充值金额须大于零。");
        state.setAmount(amount);
        if (state.current === 0) { state.setCurrent(1); return; }
        const data = await write<{ payment: { id: string } }>("/wallet/topups", { amount_cents: amount }, { key: state.requestKey.current });
        state.setPayment({ id: data.payment.id, amount }); state.setCurrent(PAYMENT_STEP);
      });
    } finally { state.locked.current = false; state.setValidating(false); }
  }
  async function settle() {
    if (!state.payment || state.complete) return;
    await state.feedback.run(async () => {
      await write(`/payment/${state.payment?.id}/mock`, { status: "succeeded" });
      state.setComplete(true); await reload();
    });
  }
  function restart() {
    if (state.busy || !state.complete) return;
    state.form.resetFields(); state.setPayment(undefined); state.setComplete(false); state.setCurrent(0); state.changed();
  }
  return { ...state, advance, settle, restart };
}

function PaymentResult({ state, currency }: { state: ReturnType<typeof useTopUpFlow>; currency: string }) {
  if (!state.payment) return null;
  return <div className="af-flow-success">
    <div className="af-mall-key-value"><span>{state.complete ? "已充值金额" : "待充值金额"}</span>
      <strong>{money(state.payment.amount, currency)}</strong></div>
    <Typography.Paragraph type="secondary" copyable={{ text: state.payment.id }}>支付单 {state.payment.id}</Typography.Paragraph>
    {state.complete ? <><Alert type="success" showIcon title="模拟充值已完成" />
      <Button disabled={state.busy} onClick={state.restart}>再充一笔</Button></>
      : <Button type="primary" loading={state.busy} onClick={() => void state.settle()}>模拟完成充值</Button>}
    <Link to={`/shop/payment-result?payment_id=${encodeURIComponent(state.payment.id)}`}>查看支付结果</Link>
  </div>;
}

export function TopUpFlow(props: TopUpProps) {
  const state = useTopUpFlow(props);
  const name = useId();
  const payment = state.current === PAYMENT_STEP;
  return <FlowFrame titles={TITLES} current={state.current} onBack={state.back} busy={state.busy} backDisabled={payment}>
    <Form name={name} form={state.form} layout="vertical" requiredMark="optional" disabled={state.busy} onValuesChange={state.changed}
      onSubmitCapture={(event) => { event.preventDefault(); event.stopPropagation(); void state.advance(); }} hidden={payment}>
      <div hidden={state.current !== 0}><FormFields fields={[{
        name: "amount_cents", label: `充值金额（${props.currency}）`, kind: "money", currency: props.currency,
        min: 1 / MINOR_UNITS, placeholder: "0.00", hint: "最多保留两位小数。",
      }]} /></div>
      {state.current === 1 && <div className="af-form-review"><dl><div><dt>充值金额</dt>
        <dd>{money(state.amount, props.currency)}</dd></div>
        <div><dt>到账方式</dt><dd>完成模拟支付后，计入商城钱包可用余额。</dd></div></dl></div>}
      <div className="af-form-flow-actions">
        {state.current > 0 && <Button disabled={state.busy} onClick={() => state.back(0)}>上一步</Button>}
        <Button type="primary" htmlType="submit" loading={state.busy}>{state.current === 0 ? "下一步" : "创建充值单"}</Button>
      </div>
    </Form>
    {payment && <PaymentResult state={state} currency={props.currency} />}
    <ActionFeedback state={state.feedback} />
  </FlowFrame>;
}
