import { useEffect, useState } from "react";
import { Button } from "antd";
import type { Connector } from "../../api/types";
import { FlowFrame } from "../../components/common/FlowFrame";
import { JsonView } from "../../components/common/json";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useInvokeConnector } from "../../hooks/use-governance";

const TITLES = ["核对调用", "查看响应"];
type Props = { connector: Connector; onBusyChange: (busy: boolean) => void; onClose: () => void };
type InvocationResult = { connector: Connector; data: Record<string, unknown> };

export function ConnectorInvokeFlow({ connector, onBusyChange, onClose }: Props) {
  const invoke = useInvokeConnector();
  const feedback = useActionFeedback();
  const [result, setResult] = useState<InvocationResult>();
  const reviewed = result?.connector ?? connector;
  useEffect(() => { onBusyChange(feedback.busy); }, [feedback.busy, onBusyChange]);
  async function call() {
    if (result !== undefined || !connector.enabled) return;
    await feedback.run(async () => {
      const data = await invoke.mutateAsync(connector.name);
      setResult({ connector, data });
    });
  }
  return <FlowFrame titles={TITLES} current={result === undefined ? 0 : 1} onBack={() => undefined}
    busy={feedback.busy} backDisabled focusOnMount>
    <div className="af-form-review"><dl>
      <div><dt>连接器</dt><dd>{reviewed.name}</dd></div>
      <div><dt>服务地址</dt><dd>{reviewed.base_url}</dd></div>
      <div><dt>用途</dt><dd>{reviewed.description || "未填写说明"}</dd></div>
    </dl></div>
    {result === undefined ? <p className="af-work-help">
      {connector.enabled ? "本次以空参数调用该服务，实际处理由连接器决定。核对连接器和服务地址后再发起调用。" : "该连接器已停用，无法发起调用。"}
    </p> : <div className="af-work-stack"><p role="status" className="af-work-help">已收到调用响应，请核对返回内容中的业务结果。</p>
      <JsonView data={result.data} title="服务响应" /></div>}
    <ActionFeedback state={feedback} /><div className="af-form-flow-actions">
      <Button disabled={feedback.busy} onClick={onClose}>{result === undefined ? "取消" : "返回连接器列表"}</Button>
      {result === undefined && <Button type="primary" loading={feedback.busy} disabled={!connector.enabled}
        onClick={() => void call()}>确认试调用</Button>}
    </div>
  </FlowFrame>;
}
