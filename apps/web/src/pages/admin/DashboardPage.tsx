import { Alert, Button, Spin } from "antd";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/admin";
import { useAnalyticsSummary } from "../../hooks/use-analytics";
import { useFeatures } from "../../plugins/features";
import { DashboardAttention, DashboardCosts, DashboardMetrics, DashboardWorkload, finding } from "./dashboard-parts";

export function DashboardPage() {
  const query = useAnalyticsSummary();
  const { enabled } = useFeatures();
  const destination = enabled("handoff") ? "/admin/handoffs" : enabled("ticket") ? "/admin/tickets" : "/";
  return <div className="af-page">
    <PageHeader title="运营看板" subtitle={finding(query.data)}
      actions={<Link to={destination}><Button type="primary">{destination === "/" ? "前往对话台" : "处理客服任务"}</Button></Link>} />
    {query.isError && <Alert type="error" showIcon title="运营数据暂时无法读取"
      description={query.error instanceof Error ? query.error.message : String(query.error)}
      action={<Button onClick={() => void query.refetch()}>重试</Button>} />}
    <Spin spinning={query.isLoading}>
      {query.data ? <><DashboardMetrics summary={query.data} />
        <div className="af-dashboard-grid"><DashboardWorkload summary={query.data} /><DashboardAttention summary={query.data} /></div>
        <DashboardCosts summary={query.data} /></> :
        <p className="af-dashboard-zero">{query.isLoading ? "正在读取运营数据…" : "暂无运营数据。"}</p>}
    </Spin>
  </div>;
}
