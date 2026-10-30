import { useState } from "react";
import { Alert, Button, Checkbox, Collapse, Form, Input, Radio, Tag, Typography } from "antd";
import { FlowFrame } from "../components/common/FlowFrame";
import { GuidedForm } from "../components/common/GuidedForm";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { ActionForm, type Row } from "./shared";
import { setToken } from "../api/client";
import { write } from "./client";

const SETUP_TITLES = ["添加验证器", "验证并启用", "保存恢复码"];
const RECOVERY_STEP = SETUP_TITLES.length - 1;
const CODE_RULES = [{ required: true, pattern: /^\d{6}$/, message: "请填写 6 位验证器验证码。" }];
type SetupEvents = { onStarted: () => void; onEnabled: () => void };

export function securitySignOut() { setToken(null); window.location.assign("/shop/account"); }

function RecoveryCodes({ codes }: { codes: string[] }) {
  const [saved, setSaved] = useState(false);
  return <div className="af-security-block">
    <Alert type="warning" showIcon title="恢复码仅展示一次" description="每个恢复码仅可使用一次。请离线保存，验证器不可用时可用于登录。" />
    <div className="af-recovery-codes">{codes.map((code) => <Typography.Paragraph key={code} copyable={{ text: code }}>
      <code>{code}</code></Typography.Paragraph>)}</div>
    <Checkbox checked={saved} onChange={(event) => setSaved(event.target.checked)}>我已保存恢复码</Checkbox>
    <Button type="primary" disabled={!saved} onClick={securitySignOut}>完成设置，重新登录</Button>
  </div>;
}

function useMfaSetup(events: SetupEvents) {
  const [current, setCurrent] = useState(0);
  const [secret, setSecret] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [confirming, setConfirming] = useState(false);
  const feedback = useActionFeedback();
  const busy = feedback.busy || confirming;
  function back(index: number) {
    if (!busy && !codes.length && index < current) setCurrent(index);
  }
  async function setup() {
    await feedback.run(async () => {
      const data = await write<{ secret: string }>("/account/mfa/setup", {});
      setSecret(data.secret); events.onStarted();
    });
  }
  async function enable(values: Row) {
    const data = await write<{ recovery_codes: string[] }>("/account/mfa/enable", { totp: values.totp });
    setCodes(data.recovery_codes); setSecret(""); setConfirming(false); setCurrent(RECOVERY_STEP);
    events.onEnabled();
  }
  return { current, secret, codes, busy, feedback, setup, enable, back, setConfirming,
    next: () => { if (secret && !busy) setCurrent(1); } };
}

function SetupMfa(events: SetupEvents) {
  const state = useMfaSetup(events);
  return <FlowFrame titles={SETUP_TITLES} current={state.current} onBack={state.back}
    busy={state.busy} backDisabled={Boolean(state.codes.length)}>
    <div hidden={state.current !== 0} className="af-flow-stage">
      <p className="af-flow-description">将 AskFlow 密钥添加到您的验证器，再使用它生成的验证码完成启用。</p>
      {state.secret && <Typography.Paragraph copyable={{ text: state.secret }}><code>{state.secret}</code></Typography.Paragraph>}
      <ActionFeedback state={state.feedback} />
      <div className="af-form-flow-actions"><Button type="primary" loading={state.busy}
        onClick={() => state.secret ? state.next() : void state.setup()}>{state.secret ? "下一步" : "生成验证器密钥"}</Button></div>
    </div>
    {!state.codes.length && <div hidden={state.current !== 1}>
      <ActionForm label="验证并启用" guided={false} submit={state.enable} onBusyChange={state.setConfirming} disabled={!state.secret}
        extra={<Button disabled={state.busy} onClick={() => state.back(0)}>上一步</Button>}
        fields={[{ name: "totp", label: "验证器验证码", inputMode: "numeric", autoComplete: "one-time-code", rules: CODE_RULES }]} />
    </div>}
    {state.current === RECOVERY_STEP && <RecoveryCodes codes={state.codes} />}
  </FlowFrame>;
}

function DisableMfa() {
  const [form] = Form.useForm();
  const method = Form.useWatch("method", form) ?? "totp";
  const feedback = useActionFeedback();
  async function disable(values: Row) {
    return feedback.run(async () => {
      await write("/account/mfa/disable", { [String(values.method)]: values[String(values.method)] });
      securitySignOut();
    });
  }
  return <GuidedForm form={form} initialValues={{ method: "totp" }} onFinish={disable}
    submitLabel="关闭验证并退出全部设备" onValuesChange={feedback.clear} feedback={<ActionFeedback state={feedback} />}
    steps={[{ title: "输入验证凭证", fields: ["method", "totp", "recovery_code"], content: <>
      <Form.Item name="method" label="验证方式"><Radio.Group options={[
        { value: "totp", label: "验证器" }, { value: "recovery_code", label: "恢复码" },
      ]} /></Form.Item>
      {method === "totp" ? <Form.Item name="totp" label="验证器验证码" rules={CODE_RULES}>
        <Input inputMode="numeric" autoComplete="one-time-code" /></Form.Item>
        : <Form.Item name="recovery_code" label="恢复码" rules={[{ required: true, whitespace: true, message: "请填写一个未使用的恢复码。" }]}>
          <Input.Password autoComplete="off" /></Form.Item>}
    </> }]} review={(values) => <dl><div><dt>操作</dt><dd>关闭当前账号的二步验证</dd></div>
      <div><dt>验证方式</dt><dd>{values.method === "totp" ? "验证器验证码" : "恢复码"}已填写</dd></div>
      <div><dt>完成后的变化</dt><dd>全部设备将退出登录，现有恢复码失效。</dd></div></dl>} />;
}

export function MfaSettings({ enabled }: { enabled: boolean }) {
  const [started, setStarted] = useState(false);
  const [activated, setActivated] = useState(false);
  return <section className="af-security-block"><div className="af-security-heading">
    <h3>二步验证</h3><Tag>{enabled || activated ? "已开启" : "未开启"}</Tag></div>
    <p className="af-mall-note">开启后，登录需要密码和验证器验证码。请保留恢复码以备验证器不可用。</p>
    {enabled && !started ? <Collapse ghost items={[{ key: "disable", label: "关闭二步验证", children: <DisableMfa /> }]} />
      : <SetupMfa onStarted={() => setStarted(true)} onEnabled={() => setActivated(true)} />}
  </section>;
}
