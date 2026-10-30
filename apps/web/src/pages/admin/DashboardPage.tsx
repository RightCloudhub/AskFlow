import { Alert, Button, Skeleton } from "antd";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/admin";
import { RefreshButton } from "../../components/admin/workspace";
import { useAnalyticsSummary } from "../../hooks/use-analytics";
import { useFeatures } from "../../plugins/features";
import { DashboardAttention, DashboardCosts, DashboardLinks, DashboardMetrics, DashboardWorkload, finding } from "./dashboard-parts";
const SKELETON_ROWS = 4;

export function DashboardPage() {
  const query = useAnalyticsSummary();
  const { enabled } = useFeatures();
  const destination = enabled("handoff") ? "/admin/handoffs" : enabled("ticket") ? "/admin/tickets" : "/";
  return <div className="af-page">
    <PageHeader title="服务运营" subtitle={finding(query.data)} actions={<>
      <RefreshButton query={query} /><Link to={destination}><Button type="primary">
        {destination === "/" ? "打开客服工作台" : "处理客服任务"}</Button></Link></>} />
    {query.isError && <Alert type="error" showIcon title="运营数据暂时无法读取"
      description={query.error instanceof Error ? query.error.message : String(query.error)}
      action={<Button onClick={() => void query.refetch()}>重试</Button>} />}
    {query.isLoading && !query.data && <Skeleton paragraph={{ rows: SKELETON_ROWS }} />}
    {query.data && <><DashboardMetrics summary={query.data} />
      <div className="af-dashboard-body"><div className="af-dashboard-main">
        <DashboardWorkload summary={query.data} /><DashboardCosts summary={query.data} />
      </div><div className="af-dashboard-aside"><DashboardAttention summary={query.data} /><DashboardLinks /></div></div>
    </>}
    {!query.isLoading && !query.data && <p className="af-dashboard-zero">暂无运营数据。</p>}
  </div>;
}
