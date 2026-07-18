import { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Descriptions,
  Drawer,
  Empty,
  List,
  Select,
  Space,
  Tag,
  Typography,
} from "antd";
import { DiffOutlined, RollbackOutlined } from "@ant-design/icons";
import {
  useDocumentDiff,
  useDocumentGenerations,
  useRollbackDocument,
} from "../../hooks/use-documents";
import type { DocumentRow } from "../../api/types";

const { Text, Paragraph } = Typography;

type Props = {
  doc: DocumentRow | null;
  open: boolean;
  onClose: () => void;
};

export function DocumentRevisionDrawer({ doc, open, onClose }: Props) {
  const id = doc?.id ?? null;
  const gensQ = useDocumentGenerations(open ? id : null);
  const gens = gensQ.data?.generations ?? [];
  const current = gensQ.data?.current_generation;

  const pair = useMemo(() => {
    if (gens.length < 2) return { from: null as number | null, to: null as number | null };
    const sorted = [...gens].sort((a, b) => a - b);
    return {
      from: sorted[sorted.length - 2],
      to: sorted[sorted.length - 1],
    };
  }, [gens]);

  const [from, setFrom] = useState<number | null>(null);
  const [to, setTo] = useState<number | null>(null);
  const effFrom = from ?? pair.from;
  const effTo = to ?? pair.to;

  const diffQ = useDocumentDiff(open ? id : null, effFrom, effTo);
  const rollback = useRollbackDocument();

  async function onRollback(generation: number) {
    if (!id) return;
    await rollback.mutateAsync({ id, generation });
  }

  return (
    <Drawer
      title={doc ? `版本 · ${doc.title || doc.filename}` : "版本"}
      open={open}
      onClose={onClose}
      width={480}
      destroyOnClose
    >
      {!doc ? null : (
        <>
          <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
            <Descriptions.Item label="当前 generation">
              <Tag color="blue">{current ?? doc.generation ?? "—"}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="分块数">{doc.chunk_count}</Descriptions.Item>
            <Descriptions.Item label="状态">{doc.status}</Descriptions.Item>
          </Descriptions>

          <Text type="secondary">历史版本</Text>
          {gensQ.isLoading ? (
            <Paragraph type="secondary">加载中…</Paragraph>
          ) : gens.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="尚无修订快照"
              style={{ margin: "16px 0" }}
            />
          ) : (
            <List
              size="small"
              style={{ marginTop: 8, marginBottom: 16 }}
              dataSource={[...gens].sort((a, b) => b - a)}
              renderItem={(g) => (
                <List.Item
                  actions={[
                    <Button
                      key="rb"
                      size="small"
                      icon={<RollbackOutlined />}
                      disabled={g === current}
                      loading={
                        rollback.isPending &&
                        rollback.variables?.generation === g
                      }
                      onClick={() => void onRollback(g)}
                    >
                      回滚
                    </Button>,
                  ]}
                >
                  <Tag color={g === current ? "processing" : "default"}>
                    g{g}
                    {g === current ? " · 当前" : ""}
                  </Tag>
                </List.Item>
              )}
            />
          )}

          <Space wrap style={{ marginBottom: 12 }}>
            <Select
              placeholder="from"
              style={{ width: 100 }}
              value={effFrom ?? undefined}
              options={gens.map((g) => ({ value: g, label: `g${g}` }))}
              onChange={setFrom}
            />
            <Select
              placeholder="to"
              style={{ width: 100 }}
              value={effTo ?? undefined}
              options={gens.map((g) => ({ value: g, label: `g${g}` }))}
              onChange={setTo}
            />
            <Button icon={<DiffOutlined />} loading={diffQ.isFetching} disabled>
              差异
            </Button>
          </Space>

          {diffQ.isError ? (
            <Alert
              type="error"
              showIcon
              message={
                diffQ.error instanceof Error
                  ? diffQ.error.message
                  : "差异加载失败"
              }
            />
          ) : null}

          {diffQ.data ? (
            <div className="af-diff-panel">
              <Text strong>
                g{diffQ.data.from_generation} → g{diffQ.data.to_generation}
              </Text>
              <Paragraph type="secondary" style={{ marginBottom: 8 }}>
                未变 {diffQ.data.unchanged_count} · 新增{" "}
                {diffQ.data.added.length} · 删除 {diffQ.data.removed.length}
              </Paragraph>
              <Text type="success">新增分块</Text>
              <List
                size="small"
                dataSource={diffQ.data.added}
                locale={{ emptyText: "无" }}
                renderItem={(t, i) => (
                  <List.Item>
                    <Paragraph
                      ellipsis={{ rows: 3 }}
                      style={{ margin: 0, color: "var(--success)" }}
                    >
                      [{i + 1}] {t}
                    </Paragraph>
                  </List.Item>
                )}
              />
              <Text type="danger">删除分块</Text>
              <List
                size="small"
                dataSource={diffQ.data.removed}
                locale={{ emptyText: "无" }}
                renderItem={(t, i) => (
                  <List.Item>
                    <Paragraph
                      ellipsis={{ rows: 3 }}
                      style={{ margin: 0, color: "var(--danger)" }}
                    >
                      [{i + 1}] {t}
                    </Paragraph>
                  </List.Item>
                )}
              />
            </div>
          ) : gens.length < 2 ? (
            <Alert
              type="info"
              showIcon
              message="至少两个版本后可对比分块差异"
            />
          ) : null}
        </>
      )}
    </Drawer>
  );
}
