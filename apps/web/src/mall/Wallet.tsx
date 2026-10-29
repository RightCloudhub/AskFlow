import { useCallback, useState } from "react";
import { Alert, Button, Card, List, Space, Statistic, Typography } from "antd";
import { Link } from "react-router-dom";
import { mall, money, write } from "./client";
import { ActionForm, Feedback, useLoad, type Page, type Row } from "./shared";
import { useFeatures } from "../plugins/features";

type Balance = { available_cents: number; frozen_cents: number; currency: string };

export function Wallet() {
  const { enabled } = useFeatures();
  const [cursor, setCursor] = useState("");
  const loader = useCallback(() => Promise.all([mall<Balance>("/wallet"), mall<Page<Row>>(`/wallet/entries?cursor=${encodeURIComponent(cursor)}`)]), [cursor]);
  const query = useLoad(loader);
  const [payment, setPayment] = useState("");
  const [error, setError] = useState("");
  const balance = query.data?.[0];
  return <Card title="我的钱包"><Feedback error={error || query.error} loading={query.loading} />
    <Space><Statistic title="可用余额" value={money(balance?.available_cents ?? 0)} />
      <Statistic title="冻结金额" value={money(balance?.frozen_cents ?? 0)} /></Space>
    <Alert type="info" title="当前为模拟支付网关，充值不会扣取真实银行卡资金。" />
    {enabled("mall_payment") && <ActionForm label="创建充值单" fields={[{ name: "amount_cents", label: "充值金额（分）", kind: "number" }]}
      submit={async (values) => { const data = await write<{ payment: { id: string } }>("/wallet/topups", values); setPayment(data.payment.id); }} />}
    {payment && <Button onClick={() => {
      void write(`/payment/${payment}/mock`, { status: "succeeded" }).then(query.reload).catch((e: Error) => setError(e.message));
    }}>模拟完成充值</Button>}
    <List dataSource={query.data?.[1].items} renderItem={(row) => <List.Item>
      <Typography.Text>{String(row.description)} · {money(Number(row.total_cents))}</Typography.Text>
      {enabled("mall_support") && <Link to={`/shop/messages?wallet_journal_id=${row.id}`}>联系流水客服</Link>}
    </List.Item>} />
    {query.data?.[1].next_cursor && <Button onClick={() => setCursor(query.data![1].next_cursor!)}>下一页流水</Button>}
  </Card>;
}
