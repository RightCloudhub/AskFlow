import { useCallback } from "react";
import { List } from "antd";
import { Link } from "react-router-dom";
import { mall, money } from "./client";
import { useLoad, type Page, type Row } from "./shared";
import { useFeatures } from "../plugins/features";
import { MallPage, MallPanel, formatDate } from "./presentation";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { TopUp, WalletBalances, type Balance } from "./wallet-parts";
import { FilterBar } from "../components/admin/workspace";
import { useRecordFilter } from "../components/admin/use-record-filter";

const ENTRY_LABELS: Record<string, string> = { topup: "钱包充值", refund: "订单退款", payment: "订单支付", revenue: "订单结算", referral: "邀请奖励", adjustment: "资金调整", reverse: "资金冲正" };

export function Wallet() {
  const { enabled } = useFeatures();
  const paging = useCursor();
  const balance = useLoad(useCallback(() => mall<Balance>("/wallet"), []));
  const entries = useLoad(useCallback(() => mall<Page<Row>>(`/wallet/entries?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]));
  const filter = useRecordFilter({ rows: entries.data?.items ?? [], fields: ["id", "description", "business_key"] });
  const reload = async () => { await Promise.all([balance.reload(), entries.reload()]); };
  const currency = balance.data?.currency ?? "CNY";
  return <MallPage title="我的钱包" description="可用余额、冻结资金与每笔资金流水都有记录。" actions={<QueryRefresh query={balance} />}>
    <MallPanel title="钱包概况" className="af-wallet-summary"><MallQuery query={balance}><WalletBalances balance={balance.data} /></MallQuery></MallPanel>
    <div className={enabled("mall_payment") ? "af-mall-columns af-wallet-workspace" : "af-wallet-workspace"}>
      <MallPanel title="资金流水" actions={<QueryRefresh query={entries} />}>
        <FilterBar {...filter} count={entries.data ? filter.rows.length : undefined} placeholder="搜索本页流水说明或编号" />
        <MallQuery query={entries}><List className="af-mall-feed" dataSource={filter.rows}
          locale={{ emptyText: filter.filtered ? "没有匹配的资金流水，请调整关键词。" : "暂无资金流水，充值或订单支付后会显示在这里。" }}
          renderItem={(row) => <List.Item><div className="af-wallet-journal">
            <div className="af-wallet-journal-identity"><strong>{ENTRY_LABELS[String(row.description)] ?? String(row.description || "资金变动")}</strong>
              <span>{formatDate(row.created_at)}</span>
              {enabled("mall_support") && <Link to={`/shop/messages?wallet_journal_id=${encodeURIComponent(String(row.id))}`}>联系流水客服</Link>}
            </div><strong className="af-order-amount">{money(Number(row.total_cents), String(row.currency ?? currency))}</strong>
          </div></List.Item>} /></MallQuery>
        <CursorNav paging={paging} nextCursor={entries.data?.next_cursor} loading={entries.loading} />
      </MallPanel>
      {enabled("mall_payment") && balance.data && <TopUp reload={reload} currency={currency} />}
    </div>
  </MallPage>;
}
