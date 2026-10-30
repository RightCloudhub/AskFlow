import { useCallback, useState } from "react";
import { Alert, Button, List, Statistic } from "antd";
import { Link } from "react-router-dom";
import { mall, money, write } from "./client";
import { ActionForm, Feedback, useLoad, type Page, type Row } from "./shared";
import { useFeatures } from "../plugins/features";
import { MallPage, MallPanel } from "./presentation";

type Balance = { available_cents: number; frozen_cents: number; currency: string };

function WalletBalances({ balance }: { balance?: Balance }) {
  return <div className="af-wallet-balance">
    <Statistic title="可用余额" value={balance ? money(balance.available_cents, balance.currency) : "—"} />
    <Statistic title="冻结金额" value={balance ? money(balance.frozen_cents, balance.currency) : "—"} />
  </div>;
}

function TopUp({ reload }: { reload: () => Promise<void> }) {
  const [payment, setPayment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function settle() {
    setBusy(true); setError("");
    try { await write(`/payment/${payment}/mock`, { status: "succeeded" }); await reload(); setPayment(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "充值失败"); }
    finally { setBusy(false); }
  }
  return <MallPanel title="钱包充值">
    <Alert type="info" title="当前使用模拟支付网关，充值不会扣取真实银行卡资金。" showIcon />
    <ActionForm label="创建充值单" fields={[{ name: "amount_cents", label: "充值金额（分）", kind: "number" }]}
      submit={async (values) => { const data = await write<{ payment: { id: string } }>("/wallet/topups", values); setPayment(data.payment.id); }} />
    {payment && <div className="af-mall-pagination"><Button loading={busy} onClick={() => void settle()}>模拟完成充值</Button></div>}
    <Feedback error={error} />
  </MallPanel>;
}

export function Wallet() {
  const { enabled } = useFeatures();
  const [cursor, setCursor] = useState("");
  const loader = useCallback(() => Promise.all([mall<Balance>("/wallet"), mall<Page<Row>>(
    `/wallet/entries?cursor=${encodeURIComponent(cursor)}`
  )]), [cursor]);
  const query = useLoad(loader);
  const balance = query.data?.[0];
  return <MallPage title="我的钱包" description="查看可用余额、冻结金额与每一笔资金变动。">
    <Feedback {...query} /><WalletBalances balance={balance} />
    <div className={enabled("mall_payment") ? "af-mall-columns" : undefined}>
      <MallPanel title="资金流水">
        <List className="af-mall-feed" dataSource={query.data?.[1].items} locale={{ emptyText: "暂无资金流水。" }}
          renderItem={(row) => <List.Item><div className="af-wallet-journal">
            <div className="af-wallet-journal-identity"><span>{String(row.description ?? "钱包变动")}</span>
              {enabled("mall_support") && <Link to={`/shop/messages?wallet_journal_id=${row.id}`}>联系流水客服</Link>}
            </div><strong className="af-order-amount">{money(Number(row.total_cents), String(row.currency ?? balance?.currency ?? "CNY"))}</strong>
          </div></List.Item>} />
        {query.data?.[1].next_cursor && <div className="af-mall-pagination">
          <Button onClick={() => setCursor(query.data![1].next_cursor!)}>下一页流水</Button>
        </div>}
      </MallPanel>
      {enabled("mall_payment") && <TopUp reload={query.reload} />}
    </div>
  </MallPage>;
}
