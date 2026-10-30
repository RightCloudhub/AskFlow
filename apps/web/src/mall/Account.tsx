import { useState } from "react";
import { Alert, Space, Tabs, Typography } from "antd";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getToken, setToken } from "../api/client";
import { write } from "./client";
import { ActionForm, type Row } from "./shared";
import { AccountSettings } from "./AccountSettings";
import { Verification, type Proof } from "./Verification";
import { AuthFrame } from "../pages/auth/auth-frame";
import { PASSWORD_HINT, PASSWORD_RULES } from "./form-fields";
import { loginReturnPath } from "../pages/auth/return-path";

const AUTH_COPY: Record<string, { title: string; description: string }> = {
  login: { title: "登录商城账号", description: "管理订单、钱包与售后服务。" },
  register: { title: "创建商城账号", description: "验证联系方式，建立您的购买与服务记录。" },
  "code-login": { title: "使用验证码登录", description: "通过已绑定的邮箱或手机号验证身份。" },
  reset: { title: "找回账号密码", description: "验证身份后，为账号设置新的密码。" },
};

export function Account() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [tab, setTab] = useState(params.get("invite") ? "register" : "login");
  const copy = AUTH_COPY[tab] ?? AUTH_COPY.login;
  async function login(values: Row) {
    const data = await write<{ access_token: string }>("/account/login", { ...values, device: deviceId() });
    setToken(data.access_token); navigate(loginReturnPath(params.get("next"), "/shop"), { replace: true });
  }
  if (getToken()) return <AccountSettings />;
  return <AuthFrame title={copy.title} description={copy.description} variant="commerce">
    <Tabs activeKey={tab} onChange={setTab} destroyOnHidden items={[
    { key: "login", label: "登录", children: <ActionForm label="登录" submit={login} guided={false} fields={[
      { name: "identifier", label: "用户名 / 邮箱 / 手机号", autoComplete: "username" },
      { name: "password", label: "密码", kind: "password", autoComplete: "current-password" },
      { name: "totp", label: "二步验证码", required: false, inputMode: "numeric", autoComplete: "one-time-code", hint: "开启二步验证后填写；与恢复码任选其一。" },
      { name: "recovery_code", label: "恢复码", kind: "password", required: false, autoComplete: "off" },
    ]} /> },
    { key: "register", label: "注册", children: <Registration /> },
    { key: "code-login", label: "验证码登录", children: <CodeLogin login={login} /> },
    { key: "reset", label: "找回密码", children: <PasswordReset /> },
  ]} />
  </AuthFrame>;
}

function CodeLogin({ login }: { login: (values: Row) => Promise<void> }) {
  const [proof, setProof] = useState<Proof>();
  return <Space direction="vertical" style={{ width: "100%" }}>
    <Verification purpose="login" onProof={setProof} />
    {proof && <ActionForm label="登录" submit={(values) => login({ ...values, ...proof, device: deviceId() })} fields={[
      { name: "identifier", label: "已验证的邮箱或手机号" },
      { name: "totp", label: "二步验证码（如已开启）", required: false },
      { name: "recovery_code", label: "或一次性恢复码", required: false, kind: "password" },
    ]} />}
  </Space>;
}

function Registration() {
  const [params] = useSearchParams();
  const [proof, setProof] = useState<Proof>();
  return <Space direction="vertical" style={{ width: "100%" }}>
    <Verification purpose="register" onProof={setProof} />
    {proof && <ActionForm label="创建账号" initial={{ referral_code: params.get("invite") ?? "" }} fields={[
      { name: "username", label: "用户名", autoComplete: "username" },
      { name: "password", label: "密码", kind: "password", hint: PASSWORD_HINT, rules: PASSWORD_RULES, autoComplete: "new-password" },
      { name: "referral_code", label: "邀请码（可选）", required: false },
    ]} successMessage="账号已创建，请切换到登录。" submit={(values) => write("/account/register", { ...values, ...proof, device: deviceId() })} />}
    <Typography.Text type="secondary">注册后可在账号设置中管理资料与登录安全。</Typography.Text>
  </Space>;
}

function PasswordReset() {
  const [proof, setProof] = useState<Proof>();
  return <><Alert type="info" title="通过已绑定的邮箱或手机号验证身份" />
    <Verification purpose="password-reset" onProof={setProof} />
    {proof && <ActionForm label="重置密码" successMessage="密码已重置，请使用新密码登录。" fields={[
      { name: "new_password", label: "新密码", kind: "password", hint: PASSWORD_HINT, rules: PASSWORD_RULES, autoComplete: "new-password" }]}
      submit={(values) => write("/account/password/reset", { ...values, ...proof })} />}</>;
}

function deviceId() {
  const key = "mall_device";
  const value = localStorage.getItem(key) ?? crypto.randomUUID();
  localStorage.setItem(key, value);
  return value;
}
