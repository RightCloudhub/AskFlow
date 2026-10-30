import { useCallback, useState } from "react";
import { List, Typography } from "antd";
import { mall, money, write } from "./client";
import { ActionForm, Feedback, useLoad, type Page, type Row } from "./shared";
import { MallPage, MallPanel, MallStatus } from "./presentation";

export function Referral() {
  const [code, setCode] = useState("");
  const loader = useCallback(() => mall<Page<Row>>("/referral/rewards"), []);
  const query = useLoad(loader);
  return <MallPage title="邀请有礼" description="邀请好友完成首单，查看奖励的审核与发放进度。">
    <Feedback {...query} /><div className="af-mall-equal-columns">
      <MallPanel title="我的邀请码">
        <p className="af-product-description">奖励在售后观察期结束并通过风控后发放，仅支持单层邀请。</p>
        <div className="af-mall-pagination"><ActionForm label="获取我的邀请码" fields={[]} submit={async () => {
          const result = await write<{ code: string }>("/referral/code", {}); setCode(result.code);
        }} /></div>
        {code && <Typography.Paragraph className="af-invite-code" copyable>{code}</Typography.Paragraph>}
      </MallPanel>
      <MallPanel title="奖励记录">
        <List className="af-mall-feed" dataSource={query.data?.items} locale={{ emptyText: "暂无邀请奖励。" }}
          renderItem={(row) => <List.Item><MallStatus value={row.status} /><strong className="af-order-amount">
            {money(Number(row.amount_cents), String(row.currency ?? "CNY"))}
          </strong></List.Item>} />
      </MallPanel>
    </div>
  </MallPage>;
}
