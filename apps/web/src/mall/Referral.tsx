import { useCallback, useState } from "react";
import { Card, List, Typography } from "antd";
import { mall, money, write } from "./client";
import { ActionForm, Feedback, useLoad, type Page, type Row } from "./shared";

export function Referral() {
  const [code, setCode] = useState("");
  const loader = useCallback(() => mall<Page<Row>>("/referral/rewards"), []);
  const query = useLoad(loader);
  return <Card title="邀请有礼"><Feedback {...query} />
    <Typography.Paragraph>邀请好友完成首单，奖励在售后观察期结束并通过风控后发放。仅支持单层邀请。</Typography.Paragraph>
    <ActionForm label="获取我的邀请码" fields={[]} submit={async () => {
      const result = await write<{ code: string }>("/referral/code", {}); setCode(result.code);
    }} />
    {code && <Typography.Paragraph copyable>{code}</Typography.Paragraph>}
    <List dataSource={query.data?.items} renderItem={(row) => <List.Item>
      {money(Number(row.amount_cents))} · {String(row.status)}
    </List.Item>} />
  </Card>;
}
