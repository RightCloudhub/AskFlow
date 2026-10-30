import { useEffect, useRef, useState } from "react";
import { Button } from "antd";
import { useSearchParams } from "react-router-dom";
import { ActionForm, type Row } from "./shared";
import { Verification, type VerifiedContext } from "./Verification";
import { confirmPasswordField, PASSWORD_HINT, PASSWORD_RULES, type Field } from "./form-fields";
import { write } from "./client";

const USERNAME_MIN = 3;
const USERNAME_MAX = 64;
const REGISTRATION_FIELDS: Field[] = [
  { name: "username", label: "用户名", autoComplete: "username", rules: [
    { min: USERNAME_MIN, max: USERNAME_MAX, message: "用户名需为 3 至 64 个字符。" },
  ] },
  { name: "password", label: "密码", kind: "password", hint: PASSWORD_HINT, rules: PASSWORD_RULES, autoComplete: "new-password" },
  confirmPasswordField("password"),
  { name: "referral_code", label: "邀请码", required: false, hint: "没有邀请码可留空。" },
];
const RESET_FIELDS: Field[] = [
  { name: "new_password", label: "新密码", kind: "password", hint: PASSWORD_HINT, rules: PASSWORD_RULES, autoComplete: "new-password" },
  confirmPasswordField("new_password"),
];

export function deviceId() {
  const key = "mall_device";
  const value = localStorage.getItem(key) ?? crypto.randomUUID();
  localStorage.setItem(key, value);
  return value;
}

function AccountSuccess({ title, onLogin }: { title: string; onLogin: () => void }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  return <section className="af-flow-success">
    <h3 className="af-form-step-title" tabIndex={-1} ref={heading}>{title}</h3>
    <p>请使用账号和新设置的密码登录。</p>
    <Button type="primary" onClick={onLogin}>前往登录</Button>
  </section>;
}

type DetailsProps = { context: VerifiedContext; onDone: () => void; reset?: boolean; invite?: string };
function AccountDetails({ context, onDone, reset, invite }: DetailsProps) {
  async function submit(values: Row) {
    if (!context.proof) throw new Error("请先验证联系方式。");
    const payload = reset ? { new_password: values.new_password } : {
      username: String(values.username).trim(), password: values.password,
      referral_code: values.referral_code ?? "", device: deviceId(),
    };
    await write(reset ? "/account/password/reset" : "/account/register", { ...payload, ...context.proof });
    onDone();
  }
  return <ActionForm guided={false} label={reset ? "重置密码" : "创建账号"} submit={submit}
    initial={{ referral_code: invite ?? "" }} fields={reset ? RESET_FIELDS : REGISTRATION_FIELDS}
    disabled={!context.proof} extra={context.back} onBusyChange={context.onBusyChange} />;
}

type RegistrationProps = { onLogin: () => void; onBusyChange: (busy: boolean) => void };
export function Registration({ onLogin, onBusyChange }: RegistrationProps) {
  const [params] = useSearchParams();
  const [done, setDone] = useState(false);
  if (done) return <AccountSuccess title="账号已创建" onLogin={onLogin} />;
  return <Verification purpose="register" onBusyChange={onBusyChange} completion={{ title: "设置账号", render: (context) =>
    <AccountDetails context={context} invite={params.get("invite") ?? ""} onDone={() => { setDone(true); onBusyChange(false); }} /> }} />;
}

export function PasswordReset({ onLogin, onBusyChange }: RegistrationProps) {
  const [done, setDone] = useState(false);
  if (done) return <AccountSuccess title="密码已重置" onLogin={onLogin} />;
  return <Verification purpose="password-reset" onBusyChange={onBusyChange} completion={{ title: "设置新密码", render: (context) =>
    <AccountDetails context={context} reset onDone={() => { setDone(true); onBusyChange(false); }} /> }} />;
}
