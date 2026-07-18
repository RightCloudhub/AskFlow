import { useMemo, useState } from "react";
import { Button, Card, Col, Empty, List, Row, Spin, Table } from "antd";
import { ThunderboltOutlined } from "@ant-design/icons";
import {
  DonutChart,
  PageHeader,
  StatCard,
  StatusBadge,
  type ChartDatum,
} from "../../components/admin";
import { useSlaScan, useSlaStatus } from "../../hooks/use-ops";
import type { SlaScanResult } from "../../api/types";

const COUNT_LABELS: Record<string, string> = {
  ok: "正常",
  warning: "预警",
  breached: "违约",
  pending: "待处理",
  processing: "处理中",
};

const PRIORITY_LABELS: Record<string, string> = {
  low: "低",
  normal: "普通",
  high: "高",
  urgent: "紧急",
  p1: "P1",
  p2: "P2",
  p3: "P3",
};

export function SlaPage() {
  const [scan, setScan] = useState<SlaScanResult | null>(null);
  const statusQ = useSlaStatus();
  const scanM = useSlaScan();
  const status = statusQ.data;
  const counts = status?.counts ?? {};

  const donut: ChartDatum[] = useMemo(
    () =>
      Object.entries(counts).map(([k, v]) => ({
        key: k,
        label: COUNT_LABELS[k] ?? k,
        value: v,
        color:
          k === "breached"
            ? "#ff4d4f"
            : k === "warning"
              ? "#faad14"
              : k === "ok"
                ? "#52c41a"
                : undefined,
      })),
    [counts],
  );

  async function runScan() {
    const r = await scanM.mutateAsync();
    setScan(r);
  }

  const ticketColumns = [
    { title: "标题", dataIndex: "title" },
    {
      title: "SLA",
      dataIndex: "sla_state",
      render: (v: string) => <StatusBadge value={v} />,
    },
    {
      title: "优先级",
      dataIndex: "priority",
      render: (p: string) => PRIORITY_LABELS[p] ?? p,
    },
    {
      title: "状态",
      dataIndex: "status",
      render: (s: string) => COUNT_LABELS[s] ?? s,
    },
  ];

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="客服运营"
        title="SLA 监控"
        subtitle="服务等级协议扫描、预警与违约工单一览"
        actions={
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={scanM.isPending}
            onClick={() => void runScan()}
          >
            立即扫描并通知
          </Button>
        }
      />
      <Spin spinning={statusQ.isLoading}>
        <Row gutter={[16, 16]}>
          {Object.entries(counts).map(([k, v]) => (
            <Col xs={24} sm={12} lg={6} key={k}>
              <StatCard
                label={COUNT_LABELS[k] ?? k}
                value={v}
                tone={
                  k === "breached"
                    ? "danger"
                    : k === "warning"
                      ? "warn"
                      : "default"
                }
              />
            </Col>
          ))}
          {!Object.keys(counts).length && !statusQ.isLoading ? (
            <Col span={24}>
              <Empty description="暂无 SLA 计数" />
            </Col>
          ) : null}
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="SLA 状态分布">
              <DonutChart
                data={donut}
                centerLabel="工单"
                centerValue={String(
                  Object.values(counts).reduce((s, n) => s + n, 0),
                )}
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card
              title="最近扫描"
              extra={
                scan ? `${scan.scanned_changes} 项变更` : "点击扫描触发"
              }
            >
              <List
                size="small"
                locale={{ emptyText: "尚无扫描变更记录" }}
                dataSource={scan?.changes ?? []}
                renderItem={(c) => (
                  <List.Item>
                    <List.Item.Meta
                      title={<code className="af-mono">{c.ticket_id}</code>}
                      description={`${COUNT_LABELS[c.previous] ?? c.previous} → ${
                        COUNT_LABELS[c.current] ?? c.current
                      } · ${c.reason}`}
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>

        <Card title="预警 / 违约工单" style={{ marginTop: 16 }}>
          <Table
            size="middle"
            rowKey="id"
            dataSource={status?.tickets ?? []}
            columns={ticketColumns}
            pagination={false}
            locale={{ emptyText: "当前无预警 / 违约工单" }}
          />
        </Card>
      </Spin>
    </div>
  );
}
