import { useMemo } from "react";
import { Alert, Card, Col, Empty, Row, Spin } from "antd";
import {
  BarChart,
  DonutChart,
  HBarChart,
  PageHeader,
  StatCard,
  formatUsd,
  labelMetric,
  purposeLabel,
  type ChartDatum,
} from "../../components/admin";
import { useAnalyticsSummary } from "../../hooks/use-analytics";
import type { AnalyticsSummary } from "../../api/types";

const KPI = [
  { key: "messages", tone: "brand" as const, format: "number" as const },
  { key: "tickets_open", tone: "warn" as const, format: "number" as const },
  { key: "handoffs_queued", tone: "info" as const, format: "number" as const },
  { key: "gaps_open", tone: "warn" as const, format: "number" as const },
  { key: "sla_breached", tone: "danger" as const, format: "number" as const },
  { key: "thumbs_down", tone: "danger" as const, format: "number" as const },
  { key: "handoff_timeouts", tone: "danger" as const, format: "number" as const },
  { key: "cost_estimated_usd", tone: "ok" as const, format: "usd" as const },
];

function num(v: unknown): number {
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

function buildOpsBars(summary: AnalyticsSummary): ChartDatum[] {
  return [
    { key: "messages", label: "消息", value: num(summary.messages) },
    { key: "tickets", label: "未结工单", value: num(summary.tickets_open) },
    { key: "handoffs", label: "排队接管", value: num(summary.handoffs_queued) },
    { key: "gaps", label: "知识缺口", value: num(summary.gaps_open) },
    { key: "sla", label: "SLA 违约", value: num(summary.sla_breached) },
    { key: "timeout", label: "接管超时", value: num(summary.handoff_timeouts) },
  ];
}

function buildRiskDonut(summary: AnalyticsSummary): ChartDatum[] {
  return [
    { key: "sla", label: "SLA 违约", value: num(summary.sla_breached) },
    { key: "down", label: "差评", value: num(summary.thumbs_down) },
    { key: "timeout", label: "接管超时", value: num(summary.handoff_timeouts) },
    { key: "gaps", label: "开放缺口", value: num(summary.gaps_open) },
  ];
}

export function DashboardPage() {
  const { data: summary, error, isLoading, isError } = useAnalyticsSummary();

  const opsBars = useMemo(
    () => (summary ? buildOpsBars(summary) : []),
    [summary],
  );
  const riskDonut = useMemo(
    () => (summary ? buildRiskDonut(summary) : []),
    [summary],
  );
  const costByPurpose = useMemo(
    () =>
      (summary?.cost?.by_purpose ?? []).map((p, i) => ({
        key: p.purpose ?? `p${i}`,
        label: purposeLabel(p.purpose ?? "其他"),
        value: p.estimated_usd ?? 0,
      })),
    [summary],
  );
  const costByModel = useMemo(
    () =>
      (summary?.cost?.by_model ?? []).map((m, i) => ({
        key: m.model ?? `m${i}`,
        label: m.model || "未知模型",
        value: m.estimated_usd ?? 0,
      })),
    [summary],
  );

  const riskTotal = riskDonut.reduce((s, d) => s + d.value, 0);

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="运营总览"
        title="运营看板"
        subtitle="消息 · 工单 · 接管 · 知识缺口 · 模型成本 — 一屏决策"
      />

      {isError ? (
        <Alert
          type="error"
          showIcon
          message={error instanceof Error ? error.message : String(error)}
          style={{ marginBottom: 16 }}
        />
      ) : null}

      <Spin spinning={isLoading}>
        {!summary && !isLoading ? (
          <Empty description="暂无运营数据" />
        ) : summary ? (
          <>
            <Row gutter={[16, 16]}>
              {KPI.map((k) => (
                <Col xs={24} sm={12} md={8} lg={6} key={k.key}>
                  <StatCard
                    label={labelMetric(k.key)}
                    value={
                      (summary as Record<string, unknown>)[k.key] as number
                    }
                    tone={k.tone}
                    format={k.format}
                  />
                </Col>
              ))}
            </Row>

            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={24} lg={14}>
                <Card title="运营负载分布" extra="核心工作量对比">
                  <BarChart data={opsBars} />
                </Card>
              </Col>
              <Col xs={24} lg={10}>
                <Card title="风险与质量信号" extra="需关注项占比">
                  <DonutChart
                    data={riskDonut}
                    centerLabel="风险项"
                    centerValue={String(riskTotal)}
                  />
                </Card>
              </Col>
            </Row>

            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={24} lg={12}>
                <Card
                  title="成本 · 按用途"
                  extra={formatUsd(num(summary.cost_estimated_usd))}
                >
                  <HBarChart data={costByPurpose} format="usd" />
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title="成本 · 按模型" extra="模型费用分布">
                  <HBarChart data={costByModel} format="usd" />
                </Card>
              </Col>
            </Row>
          </>
        ) : null}
      </Spin>
    </div>
  );
}
