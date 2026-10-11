import { useState } from "react";
import { Alert, Button, Card, Space } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { PageHeader } from "../../components/admin";
import { HandoffInbox } from "../../components/handoff/Inbox";
import { SessionDetail } from "../../components/handoff/SessionDetail";
import {
  useClaimHandoff,
  useHandoffs,
  useReturnHandoff,
} from "../../hooks/use-ops";
import { useMe } from "../../hooks/use-auth";
import type { Handoff } from "../../api/types";

export function HandoffsPage() {
  const [selected, setSelected] = useState<Handoff | null>(null);
  const [error, setError] = useState<string | null>(null);
  const handoffsQ = useHandoffs();
  const me = useMe();
  const claim = useClaimHandoff();
  const ret = useReturnHandoff();

  async function onClaim(id: string) {
    setError(null);
    try {
      const row = await claim.mutateAsync(id);
      setSelected(row);
    } catch (e) {
      setError(e instanceof Error ? e.message : "认领失败");
    }
  }

  async function onReturn(id: string) {
    setError(null);
    try {
      await ret.mutateAsync(id);
      if (selected?.id === id) setSelected(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "交还失败");
    }
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="客服运营"
        title="人工接管"
        subtitle="转人工收件箱：认领会话或交还智能助手，每 15 秒自动刷新"
        actions={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              loading={handoffsQ.isFetching}
              onClick={() => void handoffsQ.refetch()}
            >
              刷新
            </Button>
          </Space>
        }
      />
      {error ? (
        <Alert
          type="error"
          showIcon
          title={error}
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setError(null)}
        />
      ) : null}
      <Card>
        <HandoffInbox
          rows={handoffsQ.data ?? []}
          loading={handoffsQ.isLoading}
          currentUserId={me.data?.id ?? null}
          claimingId={claim.isPending ? (claim.variables ?? null) : null}
          returningId={ret.isPending ? (ret.variables ?? null) : null}
          onClaim={(id) => void onClaim(id)}
          onReturn={(id) => void onReturn(id)}
          onSelect={setSelected}
        />
      </Card>
      <SessionDetail
        open={Boolean(selected)}
        session={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
