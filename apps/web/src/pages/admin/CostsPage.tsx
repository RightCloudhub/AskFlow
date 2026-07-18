import { useMemo } from "react";
import { Card, Col, Empty, Row, Spin, Table } from "antd";
import {
  DonutChart,
  HBarChart,
  PageHeader,
  StatCard,
  formatNumber,
  formatUsd,
  purposeLabel,
  type ChartDatum,
} from "../../components/admin";
import { useCostSummary } from "../../hooks/use-governance";
import type { CostBucket } from "../../api/types";

function totals(rows: CostBucket[]) {
  return rows.reduce(
    (acc, r) => {
      acc.usd += r.estimated_usd || 0;
      acc.calls += r.calls || 0;
      acc.prompt += r.prompt_tokens || 0;
      acc.completion += r.completion_tokens || 0;
      return acc;
    },
    { usd: 0, calls: 0, prompt: 0, completion: 0 },
  );
}

export function CostsPage() {
  const costQ = useCostSummary();
  const data = costQ.data;
  const purposeRows = data?.by_purpose ?? [];
  const modelRows = data?.by_model ?? [];
  const agg = useMemo(
    () => totals(purposeRows.length ? purposeRows : modelRows),
    [purposeRows, modelRows],
  );

  const purposeChart: ChartDatum[] = purposeRows.map((r, i) => ({
    key: r.purpose ?? `p${i}`,
    label: purposeLabel(r.purpose ?? "其他"),
    value: r.estimated_usd,
  }));
  const modelChart: ChartDatum[] = modelRows.map((r, i) => ({
    key: r.model ?? `m${i}`,
    label: r.model || "未知模型",
    value: r.estimated_usd,
  }));
  const callChart: ChartDatum[] = purposeRows.map((r, i) => ({
    key: `c-${r.purpose ?? i}`,
    label: purposeLabel(r.purpose ?? "其他"),
    value: r.calls,
  }));

  const columns = [
    {
      title: "用途",
      dataIndex: "purpose",
      render: (p: string) => purposeLabel(p ?? "—"),
    },
    {
      title: "调用",
      dataIndex: "calls",
      render: (v: number) => formatNumber(v),
    },
    {
      title: "输入 Token",
      dataIndex: "prompt_tokens",
      render: (v: number) => formatNumber(v),
    },
    {
      title: "输出 Token",
      dataIndex: "completion_tokens",
      render: (v: number) => formatNumber(v),
    },
    {
      title: "费用",
      dataIndex: "estimated_usd",
      render: (v: number) => formatUsd(v),
    },
  ];

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="运营总览"
        title="成本分析"
        subtitle="按用途与模型拆分 Token 与预估费用"
      />
      <Spin spinning={costQ.isLoading}>
        {!data && !costQ.isLoading ? (
          <Empty description="暂无成本数据" />
        ) : (
          <>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} lg={6}>
                <StatCard label="预估总费用" value={agg.usd} format="usd" tone="brand" />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <StatCard label="调用次数" value={agg.calls} tone="info" />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <StatCard label="输入 Token" value={agg.prompt} />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <StatCard label="输出 Token" value={agg.completion} />
              </Col>
            </Row>

            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={24} lg={12}>
                <Card title="费用占比 · 用途" extra={formatUsd(agg.usd)}>
                  <DonutChart
                    data={purposeChart}
                    centerLabel="USD"
                    centerValue={formatUsd(agg.usd).replace("$", "")}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title="费用 · 按模型">
                  <HBarChart data={modelChart} format="usd" />
                </Card>
              </Col>
            </Row>

            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={24} lg={10}>
                <Card title="调用次数 · 用途">
                  <HBarChart data={callChart} />
                </Card>
              </Col>
              <Col xs={24} lg={14}>
                <Card title="明细表">
                  <Table
                    size="middle"
                    rowKey={(r) => r.purpose ?? r.model ?? String(Math.random())}
                    dataSource={purposeRows}
                    columns={columns}
                    pagination={false}
                    locale={{ emptyText: "暂无成本记录" }}
                  />
                </Card>
              </Col>
            </Row>
          </>
        )}
      </Spin>
    </div>
  );
}
