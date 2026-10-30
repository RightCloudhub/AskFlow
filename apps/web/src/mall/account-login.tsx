import { useCallback, useState, type ReactNode } from "react";
import { Radio } from "antd";
import { ActionForm, type Row } from "./shared";
import { Verification } from "./Verification";
import type { Field } from "./form-fields";

export type LoginAction = (values: Row) => Promise<void>;
type MfaMethod = "none" | "totp" | "recovery_code";
const MFA_OPTIONS = [
  { value: "none", label: "未开启" }, { value: "totp", label: "验证器" }, { value: "recovery_code", label: "恢复码" },
];
const MFA_FIELDS: Record<Exclude<MfaMethod, "none">, Field> = {
  totp: { name: "totp", label: "二步验证码", inputMode: "numeric", autoComplete: "one-time-code" },
  recovery_code: { name: "recovery_code", label: "恢复码", kind: "password", autoComplete: "off" },
};

function LoginFields({ login, identifier, disabled, extra, onBusyChange }: {
  login: LoginAction; identifier?: string; disabled?: boolean;
  extra?: ReactNode; onBusyChange?: (busy: boolean) => void;
}) {
  const [method, setMethod] = useState<MfaMethod>("none");
  const [busy, setBusy] = useState(false);
  const busyChanged = useCallback((value: boolean) => {
    setBusy(value); onBusyChange?.(value);
  }, [onBusyChange]);
  const fields: Field[] = identifier === undefined ? [
    { name: "identifier", label: "用户名 / 邮箱 / 手机号", autoComplete: "username" },
    { name: "password", label: "密码", kind: "password", autoComplete: "current-password" },
  ] : [];
  if (method !== "none") fields.push(MFA_FIELDS[method]);
  async function submit(values: Row) {
    await login({ identifier: identifier ?? values.identifier, password: values.password ?? "",
      totp: method === "totp" ? values.totp : "", recovery_code: method === "recovery_code" ? values.recovery_code : "" });
  }
  return <div className="af-flow-success">
    <label className="af-field"><span>二步验证</span>
      <Radio.Group aria-label="二步验证方式" value={method} options={MFA_OPTIONS} disabled={busy || disabled}
        onChange={(event) => setMethod(event.target.value)} /></label>
    <ActionForm label="登录并继续" submit={submit} fields={fields} guided={false} disabled={disabled} extra={extra}
      onBusyChange={busyChanged} />
  </div>;
}

type LoginProps = { login: LoginAction; onBusyChange: (busy: boolean) => void };
export function PasswordLogin({ login, onBusyChange }: LoginProps) {
  return <LoginFields login={login} onBusyChange={onBusyChange} />;
}

export function CodeLogin({ login, onBusyChange }: LoginProps) {
  return <Verification purpose="login" onBusyChange={onBusyChange} completion={{ title: "确认登录", render: (context) =>
    <LoginFields identifier={context.recipient} disabled={!context.proof} extra={context.back}
      onBusyChange={context.onBusyChange} login={async (values) => {
        if (!context.proof) throw new Error("请先验证联系方式。");
        await login({ ...values, ...context.proof });
      }} /> }} />;
}
