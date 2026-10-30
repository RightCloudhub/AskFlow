import { useCallback, useState } from "react";
import { Button, List, Tag } from "antd";
import { Link, useSearchParams } from "react-router-dom";
import { mall, write } from "./client";
import { ActionForm, useLoad, type Page, type Row } from "./shared";
import { MallPanel, formatDate } from "./presentation";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { useFeatures } from "../plugins/features";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { FilterBar } from "../components/admin/workspace";
import { useRecordFilter } from "../components/admin/use-record-filter";

const READ_STATES = [{ value: "all", label: "全部消息" }, { value: "unread", label: "未读" }, { value: "read", label: "已读" }];
const SUPPORT_TITLE_LIMIT = 128;

export function ServiceLinks({ row }: { row: Row }) {
  const { enabled } = useFeatures();
  return <div className="af-mall-service-record">
    {enabled("agent") && row.conversation_id != null && <Link to={`/?conversation_id=${encodeURIComponent(String(row.conversation_id))}`}>打开客服会话</Link>}
    {enabled("ticket") && row.ticket_id != null && <Link to={`/tickets?ticket_id=${encodeURIComponent(String(row.ticket_id))}`}>查看关联工单</Link>}
  </div>;
}

export function SupportRequest({ reload }: { reload: () => Promise<void> }) {
  const [params] = useSearchParams();
  const { enabled } = useFeatures();
  const [created, setCreated] = useState<Row>();
  const context = [{ name: "订单", value: params.get("order_id") }, { name: "售后申请", value: params.get("refund_id") },
    { name: "资金流水", value: params.get("wallet_journal_id") }].filter((item) => item.value);
  return <MallPanel title="联系商城客服" description="概括需要解决的问题，提交后可继续在客服会话中补充。">
    {context.length > 0 && <dl className="af-support-context">{context.map((item) => <div key={item.name}><dt>关联{item.name}</dt><dd>{item.value}</dd></div>)}</dl>}
    <ActionForm label="提交客服问题" resetOnSuccess onChange={() => setCreated(undefined)}
      successMessage="问题已提交，可打开客服会话继续沟通。" fields={[{ name: "title", label: "需要什么帮助？",
        placeholder: "例如：订单已付款，但还未收到发货通知", hint: context.length ? "客服会同时收到上方关联的业务记录。" : "可从订单、售后或资金流水中联系对应客服。",
        rules: [{ max: SUPPORT_TITLE_LIMIT, message: `请将问题概括在 ${SUPPORT_TITLE_LIMIT} 字以内。` }],
      }]} submit={async (values) => {
        const result = await write<Row>("/support", { ...values, ticket: enabled("ticket"),
          order_id: params.get("order_id"), wallet_journal_id: params.get("wallet_journal_id"), refund_id: params.get("refund_id"),
        }); setCreated(result); await reload();
      }} />
    {created && <div className="af-support-created"><ServiceLinks row={created} /></div>}
  </MallPanel>;
}

export function ServiceRecords({ query, paging }: {
  query: ReturnType<typeof useLoad<Page<Row>>>; paging: ReturnType<typeof useCursor>;
}) {
  return <MallPanel title="服务记录" actions={<QueryRefresh query={query} />}><MallQuery query={query}>
    <List className="af-mall-feed" dataSource={query.data?.items} locale={{ emptyText: "还没有服务记录，提交问题后可在这里继续跟进。" }}
      renderItem={(row) => <List.Item><div className="af-service-identity"><strong>{row.order_id ? "订单咨询" : row.refund_id ? "售后咨询" : "商城咨询"}</strong>
        <span>{formatDate(row.created_at)}</span><ServiceLinks row={row} /></div></List.Item>} />
  </MallQuery><CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} /></MallPanel>;
}

export function Notices() {
  const paging = useCursor();
  const query = useLoad(useCallback(() => mall<Page<Row>>(`/notify?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]));
  const feedback = useActionFeedback();
  const rows = (query.data?.items ?? []).map((row): Row => ({ ...row, readState: row.read_at ? "read" : "unread" }));
  const filter = useRecordFilter({ rows, fields: ["subject", "body"], statusField: "readState" });
  const unread = rows.filter((row) => !row.read_at).length;
  return <MallPanel title="站内消息" description={query.data ? `本页 ${unread} 条未读消息` : "订单、退款与资金变动的通知。"} actions={<QueryRefresh query={query} />}>
    <FilterBar {...filter} count={query.data ? filter.rows.length : undefined} placeholder="搜索本页消息" options={READ_STATES} />
    <ActionFeedback state={feedback} /><MallQuery query={query}>
      <List className="af-mall-feed af-notice-list" dataSource={filter.rows}
        locale={{ emptyText: filter.filtered ? "没有匹配的消息，试试清除筛选。" : "暂无站内消息，新的业务通知会显示在这里。" }} renderItem={(row) => <List.Item>
          <div className="af-mall-message"><div className="af-notice-title"><strong>{String(row.subject || "业务通知")}</strong>{!row.read_at && <Tag>未读</Tag>}</div>
            <p>{String(row.body ?? "")}</p><span className="af-record-secondary">{formatDate(row.created_at)}</span></div>
          {!row.read_at && <Button type="text" disabled={feedback.busy} onClick={() => void feedback.run(async () => {
            await write(`/notify/${row.id}/read`, {}); await query.reload();
          }, "消息已标为已读。")}>标为已读</Button>}
        </List.Item>} />
    </MallQuery><CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
  </MallPanel>;
}
