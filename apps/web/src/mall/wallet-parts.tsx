import { useState } from "react";
import { Alert, Button, Typography } from "antd";
import { Link } from "react-router-dom";
import { money, write } from "./client";
import { ActionForm } from "./shared";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { MINOR_UNITS } from "./form-fields";
import { MallPanel } from "./presentation";

export type Balance = { available_cents: number; frozen_cents: number; currency: string };
type TopUpPayment = { id: string; amount: number };

export function WalletBalances({ balance }: { balance?: Balance }) {
  return <dl className="af-wallet-overview"><div><dt>可用余额</dt>
    <dd>{balance ? money(balance.available_cents, balance.currency) : "—"}</dd><p>可用于订单支付</p></div>
    <div><dt>冻结金额</dt><dd>{balance ? money(balance.frozen_cents, balance.currency) : "—"}</dd>
      <p>处理中订单占用的资金</p></div></dl>;
}

export function TopUp({ reload, currency }: { reload: () => Promise<void>; currency: string }) {
  const [payment, setPayment] = useState<TopUpPayment>();
  const feedback = useActionFeedback();
  async function settle() {
    if (!payment) return;
    await write(`/payment/${payment.id}/mock`, { status: "succeeded" });
    setPayment(undefined); await reload();
  }
  return <MallPanel title="钱包充值" description="输入充值金额，确认支付后计入可用余额。">
    <Alert type="info" title="模拟支付" description="当前使用模拟支付网关，充值不会扣取真实银行卡资金。" showIcon />
    <ActionFeedback state={feedback} />
    {payment ? <div className="af-topup-pending"><div className="af-mall-key-value"><span>待充值金额</span><strong>{money(payment.amount, currency)}</strong></div>
      <Typography.Paragraph type="secondary" copyable={{ text: payment.id }}>支付单 {payment.id}</Typography.Paragraph>
      <Button type="primary" loading={feedback.busy} onClick={() => void feedback.run(settle, "模拟充值已完成，余额已更新。")}>模拟完成充值</Button>
      <Link to={`/shop/payment-result?payment_id=${encodeURIComponent(payment.id)}`}>查看支付结果</Link>
    </div> : <ActionForm label="创建充值单" fields={[{ name: "amount_cents", label: `充值金额（${currency}）`, kind: "money", currency,
      min: 1 / MINOR_UNITS, placeholder: "0.00", hint: "最多保留两位小数。" }]} submit={async (values) => {
        const data = await write<{ payment: { id: string } }>("/wallet/topups", values);
        setPayment({ id: data.payment.id, amount: Number(values.amount_cents) });
      }} />}
  </MallPanel>;
}
