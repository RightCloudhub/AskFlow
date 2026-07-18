import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Button, Card, Segmented, Typography } from "antd";
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

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <Title level={3} style={{ margin: 0 }}>
            我的工单
          </Title>
          <Text type="secondary">查看与关闭自己创建的工单</Text>
        </div>
        <Link to="/">
          <Button type="link" icon={<ArrowLeftOutlined />}>
            返回对话
          </Button>
        </Link>
      </header>

      {err ? (
        <Alert type="error" showIcon message={err} style={{ marginBottom: 16 }} />
      ) : null}

      <Card title="新建工单" style={{ marginBottom: 16 }}>
        <TicketForm
          loading={createM.isPending}
          onSubmit={async (p) => {
            await createM.mutateAsync(p);
          }}
        />
      </Card>

      <Card
        title="工单列表"
        extra={
          <Segmented
            value={view}
            onChange={(v) => setView(v as "list" | "board")}
            options={[
              { value: "list", icon: <UnorderedListOutlined />, label: "列表" },
              { value: "board", icon: <AppstoreOutlined />, label: "看板" },
            ]}
          />
        }
      >
        {view === "list" ? (
          <TicketList
            rows={ticketsQ.data ?? []}
            loading={ticketsQ.isLoading}
            closingId={closeM.isPending ? closeM.variables ?? null : null}
            onClose={(id) => void closeM.mutateAsync(id)}
          />
        ) : (
          <TicketBoard
            rows={ticketsQ.data ?? []}
            onSelect={setSelected}
          />
        )}
      </Card>

      <TicketDetail
        open={Boolean(selected)}
        ticket={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
