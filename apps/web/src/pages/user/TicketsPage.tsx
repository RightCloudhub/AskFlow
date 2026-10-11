import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Button, Card, Col, Row, Segmented, Typography } from "antd";
import {
  ArrowLeftOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons";
import {
  useCloseTicket,
  useCreateTicket,
  useTickets,
} from "../../hooks/use-tickets";
import type { Ticket } from "../../api/types";
import { TicketBoard } from "../../components/ticket/TicketBoard";
import { TicketDetail } from "../../components/ticket/TicketDetail";
import { TicketForm } from "../../components/ticket/TicketForm";
import { TicketList } from "../../components/ticket/TicketList";

const { Title, Text } = Typography;

export function TicketsPage() {
  const [view, setView] = useState<"list" | "board">("list");
  const [selected, setSelected] = useState<Ticket | null>(null);
  const ticketsQ = useTickets();
  const createM = useCreateTicket();
  const closeM = useCloseTicket();

  const err =
    (createM.error instanceof Error && createM.error.message) ||
    (ticketsQ.error instanceof Error && ticketsQ.error.message) ||
    null;

  const rows = ticketsQ.data ?? [];
  const openCount = rows.filter(
    (t) => t.status !== "closed" && t.status !== "resolved",
  ).length;

  return (
    <div className="af-user-page">
      <header className="af-user-topbar">
        <Link to="/" className="af-user-topbar-back">
          <Button type="text" icon={<ArrowLeftOutlined />}>
            返回对话
          </Button>
        </Link>
        <span className="af-user-topbar-brand">
          <span className="brand-mark sm">AF</span>
          <strong>AskFlow</strong>
        </span>
        <span className="af-user-topbar-spacer" />
      </header>

      <div className="af-user-body">
        <div className="af-page-header">
          <div className="af-page-header-text">
            <Title level={4} className="af-page-title">
              我的工单
            </Title>
            <Text type="secondary" className="af-page-subtitle">
              共 {rows.length} 个工单，{openCount}{" "}
              个处理中。提交后客服会尽快跟进。
            </Text>
          </div>
        </div>

        {err ? (
          <Alert
            type="error"
            showIcon
            title={err}
            style={{ marginBottom: 16 }}
          />
        ) : null}

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}>
            <Card title="新建工单" className="af-user-card">
              <TicketForm
                loading={createM.isPending}
                onSubmit={async (p) => {
                  await createM.mutateAsync(p);
                }}
              />
            </Card>
          </Col>
          <Col xs={24} lg={16}>
            <Card
              title="工单列表"
              className="af-user-card"
              extra={
                <Segmented
                  value={view}
                  onChange={(v) => setView(v as "list" | "board")}
                  options={[
                    {
                      value: "list",
                      icon: <UnorderedListOutlined />,
                      label: "列表",
                    },
                    {
                      value: "board",
                      icon: <AppstoreOutlined />,
                      label: "看板",
                    },
                  ]}
                />
              }
            >
              {view === "list" ? (
                <TicketList
                  rows={rows}
                  loading={ticketsQ.isLoading}
                  closingId={
                    closeM.isPending ? (closeM.variables ?? null) : null
                  }
                  onClose={(id) => void closeM.mutateAsync(id)}
                />
              ) : (
                <TicketBoard rows={rows} onSelect={setSelected} />
              )}
            </Card>
          </Col>
        </Row>
      </div>

      <TicketDetail
        open={Boolean(selected)}
        ticket={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
