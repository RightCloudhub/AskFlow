import { useState } from "react";
import { Alert, Card, Space, Tabs, Typography } from "antd";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getToken, setToken } from "../api/client";
import { write } from "./client";
import { ActionForm, type Row } from "./shared";
import { AccountSettings } from "./AccountSettings";
import { Verification, type Proof } from "./Verification";

export function Account() {
  const navigate = useNavigate();
  async function login(values: Row) {
    const data = await write<{ access_token: string }>("/account/login", { ...values, device: deviceId() });
    setToken(data.access_token); navigate("/shop");
  }
  if (getToken()) return <AccountSettings />;
  return <Card title="商城账号"><Tabs items={[
    { key: "login", label: "登录", children: <ActionForm label="登录" submit={login} fields={[
      { name: "identifier", label: "用户名 / 邮箱 / 手机号" },
      { name: "password", label: "密码", kind: "password" },
      { name: "totp", label: "二步验证码（如已开启）", required: false },
      { name: "recovery_code", label: "或恢复码", required: false },
    ]} /> },
    { key: "register", label: "注册", children: <Registration /> },
    { key: "code-login", label: "验证码登录", children: <CodeLogin login={login} /> },
    { key: "reset", label: "找回密码", children: <PasswordReset /> },
  ]} /></Card>;
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
      { name: "username", label: "用户名" }, { name: "password", label: "密码（至少 12 位，含大小写和数字）", kind: "password" },
      { name: "referral_code", label: "邀请码（可选）", required: false },
    ]} submit={(values) => write("/account/register", { ...values, ...proof, device: deviceId() })} />}
    <Typography.Text>完成注册后请返回登录。</Typography.Text>
  </Space>;
}

function PasswordReset() {
  const [proof, setProof] = useState<Proof>();
  return <><Alert type="info" title="通过已绑定的邮箱或手机号验证身份" />
    <Verification purpose="password-reset" onProof={setProof} />
    {proof && <ActionForm label="重置密码" fields={[{ name: "new_password", label: "新密码", kind: "password" }]}
      submit={(values) => write("/account/password/reset", { ...values, ...proof })} />}</>;
}

function deviceId() {
  const key = "mall_device";
  const value = localStorage.getItem(key) ?? crypto.randomUUID();
  localStorage.setItem(key, value);
  return value;
}
