import { useCallback, useState } from "react";
import { Button, Descriptions, Drawer, List, Typography } from "antd";
import { Link, useSearchParams } from "react-router-dom";
import { mall, money } from "./client";
import { useLoad, type Page, type Row } from "./shared";
import { useFeatures } from "../plugins/features";
import { MallEmpty, MallPage, MallPanel, MallStatus, formatDate } from "./presentation";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { FilterBar } from "../components/admin/workspace";
import { useRecordFilter } from "../components/admin/use-record-filter";

function RefundDetails({ id }: { id: string }) {
  const query = useLoad(useCallback(() => mall<Row>(`/order/refunds/${encodeURIComponent(id)}`), [id]));
  return <><QueryRefresh query={query} /><MallQuery query={query}><Descriptions column={1} items={[
    { key: "id", label: "申请编号", children: <Typography.Text copyable>{id}</Typography.Text> },
    { key: "status", label: "处理状态", children: <MallStatus value={query.data?.status} /> },
    { key: "amount", label: "申请金额", children: query.data?.amount_cents == null ? "—" : money(Number(query.data.amount_cents), String(query.data.currency ?? "CNY")) },
    { key: "destination", label: "退款去向", children: query.data?.destination === "wallet" ? "商城钱包" : query.data?.destination === "original" ? "原支付方式" : "—" },
    { key: "created", label: "申请时间", children: formatDate(query.data?.created_at) },
    { key: "order", label: "关联订单", children: query.data?.order_id ? <Link to={`/shop/orders/${query.data.order_id}`}>查看订单</Link> : "—" },
  ]} /></MallQuery></>;
}

export function AfterSales() {
  const { enabled } = useFeatures();
  const paging = useCursor();
  const [detail, setDetail] = useState<string>();
  const query = useLoad(useCallback(() => mall<Page<Row>>(`/order/refunds?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]));
  const filter = useRecordFilter({ rows: query.data?.items ?? [], fields: ["id", "order_id"] });
  return <MallPage title="我的售后" description="跟进退款申请，查看每次处理的结果。" actions={<Link to="/shop/orders">查看订单</Link>}>
    <MallPanel title="售后记录" actions={<QueryRefresh query={query} />} className="af-order-records">
      <FilterBar {...filter} count={query.data ? filter.rows.length : undefined} placeholder="搜索本页申请编号或订单号" />
      <MallQuery query={query}><List className="af-order-list" dataSource={filter.rows}
        locale={{ emptyText: filter.filtered ? "没有匹配的售后申请，请调整关键词。" : "暂无售后申请，需要退款时可从订单详情发起。" }}
        renderItem={(row) => <List.Item><div className="af-order-identity">
          <Button className="af-refund-detail-link" type="text" onClick={() => setDetail(String(row.id))}>查看申请详情</Button>
          <span className="af-order-id">申请号 {String(row.id)}</span><span className="af-record-secondary">{formatDate(row.created_at)}</span>
          <div className="af-mall-service-record"><Link to={`/shop/orders/${row.order_id}`}>关联订单</Link>
            {enabled("mall_support") && <Link to={`/shop/messages?refund_id=${row.id}`}>联系售后客服</Link>}</div>
        </div><div className="af-order-result"><MallStatus value={row.status} /><strong className="af-order-amount">
          {money(Number(row.amount_cents), String(row.currency ?? "CNY"))}</strong></div></List.Item>} />
      </MallQuery><CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
    </MallPanel><Drawer title="售后申请详情" open={Boolean(detail)} onClose={() => setDetail(undefined)} destroyOnHidden>
      {detail && <RefundDetails key={detail} id={detail} />}
    </Drawer>
  </MallPage>;
}

const PAYMENT_GUIDANCE: Record<string, string> = {
  CREATED: "支付单已创建，等待完成支付。", PENDING: "支付处理中，可刷新获取最新结果。",
  SUCCEEDED: "支付已成功，可返回订单查看下一步。", FAILED: "支付未成功，请返回订单确认当前状态后再试。",
  CANCELLED: "支付已取消，可返回订单查看可用操作。", REFUNDED: "此支付已退款，可在售后记录中查看。",
};

export function PaymentResult() {
  const [params] = useSearchParams();
  const id = params.get("payment_id");
  const query = useLoad<Row>(useCallback(() => id ? mall<Row>(`/payment/${encodeURIComponent(id)}`) : Promise.resolve({}), [id]));
  return <MallPage title="支付结果" description="查看支付处理结果，并继续跟进关联订单。" actions={<Link to="/shop/orders">返回订单</Link>}>
    <MallPanel title="支付信息" actions={id && <QueryRefresh query={query} />}>
      {!id ? <MallEmpty title="尚未选择支付单"><Link to="/shop/orders">从订单查看支付记录</Link></MallEmpty> : <MallQuery query={query}>
        <div className="af-payment-result"><MallStatus value={query.data?.status} /><p>{PAYMENT_GUIDANCE[String(query.data?.status).toUpperCase()] ?? "请刷新获取支付的最新处理结果。"}</p></div>
        <Descriptions column={1} items={[
          { key: "id", label: "支付单号", children: <Typography.Text copyable>{id}</Typography.Text> },
          { key: "amount", label: "支付金额", children: query.data?.amount_cents == null ? "—" : money(Number(query.data.amount_cents), String(query.data.currency ?? "CNY")) },
          { key: "order", label: "关联订单", children: query.data?.order_id ? <Link to={`/shop/orders/${query.data.order_id}`}>查看订单详情</Link> : "—" },
        ]} />
      </MallQuery>}
    </MallPanel>
  </MallPage>;
}
