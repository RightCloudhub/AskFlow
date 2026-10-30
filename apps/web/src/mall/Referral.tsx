import { useCallback, useState } from "react";
import { Button, List, Typography } from "antd";
import { mall, money, write } from "./client";
import { useLoad, type Page, type Row } from "./shared";
import { MallPage, MallPanel, MallStatus, formatDate } from "./presentation";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";

function InvitationCode() {
  const [code, setCode] = useState("");
  const feedback = useActionFeedback();
  const link = `${window.location.origin}/shop/account?invite=${encodeURIComponent(code)}`;
  return <MallPanel title="我的邀请" description="分享邀请码或邀请链接，好友注册时填写即可建立邀请关系。">
    <ActionFeedback state={feedback} />
    {code ? <div className="af-invitation-share"><p className="af-mall-note">我的邀请码</p>
      <Typography.Paragraph className="af-invite-code" copyable={{ text: code }}>{code}</Typography.Paragraph>
      <p className="af-mall-note">邀请链接</p><Typography.Paragraph className="af-invitation-link" copyable={{ text: link }}>{link}</Typography.Paragraph>
    </div> : <Button type="primary" loading={feedback.busy} onClick={() => void feedback.run(async () => {
      const result = await write<{ code: string }>("/referral/code", {}); setCode(result.code);
    })}>获取我的邀请码</Button>}
    <dl className="af-invitation-terms"><div><dt>奖励何时发放</dt><dd>好友完成首单，售后观察期结束并通过风控后发放。</dd></div>
      <div><dt>邀请关系</dt><dd>仅支持单层邀请，具体奖励以实际审核记录为准。</dd></div></dl>
  </MallPanel>;
}

export function Referral() {
  const paging = useCursor();
  const query = useLoad(useCallback(() => mall<Page<Row>>(`/referral/rewards?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]));
  return <MallPage title="邀请有礼" description="邀请好友完成首单，跟进奖励审核与发放。">
    <div className="af-mall-columns af-referral-workspace"><InvitationCode />
      <MallPanel title="奖励记录" actions={<QueryRefresh query={query} />}><MallQuery query={query}>
        <List className="af-mall-feed" dataSource={query.data?.items} locale={{ emptyText: "暂无邀请奖励，好友完成首单后可在这里查看进度。" }}
          renderItem={(row) => <List.Item><div className="af-reward-identity"><strong>邀请奖励</strong><span>可发放时间 {formatDate(row.eligible_at)}</span></div>
            <div className="af-order-result"><MallStatus value={row.status} /><strong className="af-order-amount">{money(Number(row.amount_cents), String(row.currency ?? "CNY"))}</strong></div>
          </List.Item>} />
      </MallQuery><CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} /></MallPanel>
    </div>
  </MallPage>;
}
