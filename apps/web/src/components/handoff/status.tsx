const LABELS: Record<string, string> = {
  queued: "待认领", claimed: "人工服务中", returned: "已交还 AI", resolved: "已解决", timed_out: "已超时",
};

export function HandoffStatus({ status }: { status: string }) {
  return <span className={`af-handoff-status af-handoff-status--${status}`}>{LABELS[status] || status}</span>;
}
