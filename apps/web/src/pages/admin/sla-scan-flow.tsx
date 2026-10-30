import { useEffect, useState } from "react";
import { Button, List } from "antd";
import type { SlaScanResult } from "../../api/types";
import { FlowFrame } from "../../components/common/FlowFrame";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useSlaScan } from "../../hooks/use-ops";

const TITLES = ["核对扫描范围", "查看处理结果"];
export const SLA_LABELS: Record<string, string> = { ok: "正常", normal: "正常", warning: "预警", breached: "违约", pending: "待处理", processing: "处理中" };

export function ScanChanges({ scan }: { scan: SlaScanResult }) {
  return <div className="af-work-stack"><p role="status">本次记录了 {scan.scanned_changes} 项状态变更。</p>
    <List dataSource={scan.changes} locale={{ emptyText: "本次扫描没有发现状态变更。" }}
      renderItem={(row) => <List.Item><div className="af-record-title"><strong>{row.ticket_id}</strong>
        <small>{(SLA_LABELS[row.previous] ?? row.previous) + " → " + (SLA_LABELS[row.current] ?? row.current)}</small>
        <small>{row.reason}</small></div></List.Item>} />
  </div>;
}

export function SlaScanFlow({ onResult, onBusyChange, onClose }: {
  onResult: (scan: SlaScanResult) => void; onBusyChange: (busy: boolean) => void; onClose: () => void;
}) {
  const mutation = useSlaScan();
  const feedback = useActionFeedback();
  const [result, setResult] = useState<SlaScanResult>();
  useEffect(() => { onBusyChange(feedback.busy); }, [feedback.busy, onBusyChange]);
  async function scan() {
    if (result) return;
    await feedback.run(async () => {
      const data = await mutation.mutateAsync(); setResult(data); onResult(data);
    });
  }
  return <FlowFrame titles={TITLES} current={result ? 1 : 0} onBack={() => undefined} backDisabled busy={feedback.busy} focusOnMount>
    {result ? <ScanChanges scan={result} /> : <div className="af-form-review"><dl>
      <div><dt>扫描范围</dt><dd>检查服务时限引擎覆盖的工单，不受当前页面筛选影响。</dd></div>
      <div><dt>处理内容</dt><dd>更新 SLA 状态，并按配置触发相应通知。</dd></div>
      <div><dt>完成后</dt><dd>返回状态变更明细，可继续跟进预警或违约工单。</dd></div>
    </dl></div>}
    <ActionFeedback state={feedback} /><div className="af-form-flow-actions">
      <Button disabled={feedback.busy} onClick={onClose}>{result ? "返回监控" : "取消"}</Button>
      {!result && <Button type="primary" loading={feedback.busy} onClick={() => void scan()}>扫描并通知</Button>}
    </div>
  </FlowFrame>;
}
