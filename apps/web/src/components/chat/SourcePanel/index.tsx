import { Button, Drawer, Empty, Typography } from "antd";
import { CloseOutlined } from "@ant-design/icons";
import type { CitationSource } from "../../../api/types";
import { useSourcePanel } from "../../../stores/ui-store";

const { Text, Paragraph } = Typography;

function SourceCard({ source, index }: { source: CitationSource; index: number }) {
  const label = source.source || `来源 ${index + 1}`;
  const idx = source.index ?? index + 1;
  const snippet = (source.text || "").trim();
  return (
    <article className="af-source-card">
      <header>
        <span className="af-source-idx">[{idx}]</span>
        <Text strong ellipsis={{ tooltip: label }}>
          {label}
        </Text>
        {source.score != null ? (
          <Text type="secondary" className="af-source-score">
            {Number(source.score).toFixed(3)}
          </Text>
        ) : null}
      </header>
      <Paragraph type="secondary" className="af-source-snippet" ellipsis={{ rows: 5 }}>
        {snippet || "（无摘要）"}
      </Paragraph>
    </article>
  );
}

/** Side drawer for citation / grounding sources (RAGFlow-style). */
export function SourcePanel() {
  const { open, sources, title, close } = useSourcePanel();

  return (
    <Drawer
      title={title}
      placement="right"
      width={400}
      open={open}
      onClose={close}
      destroyOnClose
      extra={
        <Button type="text" icon={<CloseOutlined />} onClick={close} aria-label="关闭" />
      }
    >
      {sources.length === 0 ? (
        <Empty description="暂无引用" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div className="af-source-list">
          {sources.map((s, i) => (
            <SourceCard key={`${s.source ?? "s"}-${i}`} source={s} index={i} />
          ))}
        </div>
      )}
    </Drawer>
  );
}
