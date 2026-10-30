import { useEffect, useId, useState, type ReactNode } from "react";
import { Alert, Button, Form, Input } from "antd";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionFeedback } from "../components/common/action-feedback";
import { DemoCode } from "./DemoCode";
import { useVerification, type Proof, type VerificationOptions } from "./use-verification";

export type { Proof } from "./use-verification";
type VerificationState = ReturnType<typeof useVerification>;
export type VerifiedContext = {
  proof?: Proof;
  recipient: string;
  back: ReactNode;
  onBusyChange: (busy: boolean) => void;
};
type VerificationProps = VerificationOptions & {
  compact?: boolean;
  onBusyChange?: (busy: boolean) => void;
  completion?: { title: string; render: (context: VerifiedContext) => ReactNode };
};
const CODE_LENGTH = 6;
const CONTACT_RULES = [{ required: true, pattern: /^(?:[^\s@]+@[^\s@]+\.[^\s@]+|\+[\d\s()-]+)$/,
  message: "请输入有效邮箱或以 + 开头的国际格式手机号。" }];
const CODE_RULES = [{ required: true, pattern: /^\d{6}$/, message: "请输入 6 位数字验证码。" }];

function ContactForm({ state, channel }: { state: VerificationState; channel?: "email" | "sms" }) {
  const name = useId();
  const label = channel === "sms" ? "手机号" : channel === "email" ? "邮箱" : "邮箱或手机号";
  return <Form name={name} layout="vertical" requiredMark="optional" disabled={state.feedback.busy}
    onFinish={(values) => void state.send(values)} onValuesChange={state.invalidate}>
    <Form.Item name="target" label={label} rules={CONTACT_RULES}
      extra={channel === "email" ? "填写可接收验证码的邮箱。" : "手机号须包含国家区号，如 +86 13800138000。"}>
      <Input autoComplete="username" inputMode={channel === "sms" ? "tel" : "email"} placeholder={label} />
    </Form.Item>
    <div className="af-form-flow-actions"><Button type="primary" htmlType="submit" loading={state.feedback.busy}>
      {state.challenge ? "下一步" : "发送验证码"}
    </Button></div>
  </Form>;
}

function CodeForm({ state }: { state: VerificationState }) {
  const name = useId();
  if (state.proof) return <div className="af-flow-success">
    <Alert type="success" showIcon title="联系方式已验证" />
    <Button type="link" disabled={state.feedback.busy} onClick={() => void state.send({ target: state.recipient }, true)}>
      重新发送验证码
    </Button>
    <div className="af-form-flow-actions"><Button onClick={() => state.back(0)}>上一步</Button>
      <Button type="primary" onClick={() => state.setCurrent(2)}>下一步</Button></div>
  </div>;
  return <Form name={name} key={state.challenge} layout="vertical" requiredMark="optional" disabled={state.feedback.busy}
    onFinish={(values) => void state.verify(values)} onValuesChange={state.feedback.clear}>
    <Form.Item name="code" label="验证码" rules={CODE_RULES}>
      <Input inputMode="numeric" autoComplete="one-time-code" maxLength={CODE_LENGTH} placeholder="6 位数字验证码" />
    </Form.Item>
    <Button type="link" disabled={state.feedback.busy} onClick={() => void state.send({ target: state.recipient }, true)}>
      重新发送验证码
    </Button>
    <div className="af-form-flow-actions"><Button onClick={() => state.back(0)}>上一步</Button>
      <Button type="primary" htmlType="submit" loading={state.feedback.busy} disabled={!state.challenge}>验证并继续</Button></div>
    {state.challenge && <DemoCode key={state.challenge} challenge={state.challenge} />}
  </Form>;
}

export function Verification(props: VerificationProps) {
  const state = useVerification(props);
  const [submitting, setSubmitting] = useState(false);
  const busy = state.feedback.busy || submitting;
  useEffect(() => { props.onBusyChange?.(busy); }, [busy, props.onBusyChange]);
  const titles = ["联系方式", "验证码", props.completion?.title ?? "验证完成"];
  const back = <Button disabled={busy} onClick={() => state.back(1)}>上一步</Button>;
  return <FlowFrame titles={titles} current={state.current} compact={props.compact} busy={busy}
    onBack={(index) => { if (!busy) state.back(index); }}>
    {state.current > 0 && <div className="af-flow-contact"><p>
      {state.proof ? "已验证的联系方式" : "验证码已发送至"}<strong>{state.recipient}</strong>
    </p><Button type="text" disabled={busy} onClick={() => state.back(0)}>更换</Button></div>}
    <div hidden={state.current !== 0}><ContactForm state={state} channel={props.channel} /></div>
    <div hidden={state.current !== 1}><CodeForm state={state} /></div>
    <div hidden={state.current !== 2}>
      {props.completion ? props.completion.render({ proof: state.proof, recipient: state.recipient, back, onBusyChange: setSubmitting })
        : <Alert type="success" showIcon title="联系方式已验证" />}
    </div>
    <ActionFeedback state={state.feedback} />
  </FlowFrame>;
}
