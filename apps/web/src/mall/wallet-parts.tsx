import { Alert } from "antd";
import { money } from "./client";
import { MallPanel } from "./presentation";
import { TopUpFlow } from "./TopUpFlow";

export type Balance = { available_cents: number; frozen_cents: number; currency: string };

export function WalletBalances({ balance }: { balance?: Balance }) {
  return <dl className="af-wallet-overview"><div><dt>可用余额</dt>
    <dd>{balance ? money(balance.available_cents, balance.currency) : "—"}</dd><p>可用于订单支付</p></div>
    <div><dt>冻结金额</dt><dd>{balance ? money(balance.frozen_cents, balance.currency) : "—"}</dd>
      <p>处理中订单占用的资金</p></div></dl>;
}

export function TopUp({ reload, currency }: { reload: () => Promise<void>; currency: string }) {
  return <MallPanel title="钱包充值" description="输入充值金额，确认支付后计入可用余额。">
    <Alert type="info" title="模拟支付" description="当前使用模拟支付网关，充值不会扣取真实银行卡资金。" showIcon />
    <TopUpFlow reload={reload} currency={currency} />
  </MallPanel>;
}
