import { Tag } from "antd";

const PRIORITY: Record<string, { label: string; color: string }> = {
  low: { label: "低", color: "default" },
  normal: { label: "普通", color: "blue" },
  medium: { label: "中", color: "blue" },
  high: { label: "高", color: "orange" },
  urgent: { label: "紧急", color: "red" },
};

/** Ticket priority rendered as a coloured, localised tag. */
export function PriorityTag({ value }: { value: string | null | undefined }) {
  if (!value) return <span>—</span>;
  const hit = PRIORITY[value];
  return (
    <Tag color={hit?.color ?? "default"} variant="filled">
      {hit?.label ?? value}
    </Tag>
  );
}
