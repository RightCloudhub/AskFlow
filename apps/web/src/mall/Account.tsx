import { useState } from "react";
import { Tabs } from "antd";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getToken, setToken } from "../api/client";
import { write } from "./client";
import type { Row } from "./shared";
import { AccountSettings } from "./AccountSettings";
import { AuthFrame } from "../pages/auth/auth-frame";
import { loginReturnPath } from "../pages/auth/return-path";
import { Registration, PasswordReset, deviceId } from "./account-registration";
import { CodeLogin, PasswordLogin } from "./account-login";

const AUTH_COPY: Record<string, { title: string; description: string }> = {
  login: { title: "登录商城账号", description: "管理订单、钱包与售后服务。" },
  register: { title: "创建商城账号", description: "验证联系方式，再设置您的账号与密码。" },
  "code-login": { title: "使用验证码登录", description: "通过已绑定的邮箱或手机号验证身份。" },
  reset: { title: "找回账号密码", description: "验证已绑定的联系方式，再设置新的密码。" },
};

export function Account() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [tab, setTab] = useState(params.get("invite") ? "register" : "login");
  const [busy, setBusy] = useState(false);
  const copy = AUTH_COPY[tab] ?? AUTH_COPY.login;
  async function login(values: Row) {
    const data = await write<{ access_token: string }>("/account/login", { ...values, device: deviceId() });
    setToken(data.access_token); navigate(loginReturnPath(params.get("next"), "/shop"), { replace: true });
  }
  if (getToken()) return <AccountSettings />;
  return <AuthFrame title={copy.title} description={copy.description} variant="commerce">
    <Tabs activeKey={tab} onChange={setTab} destroyOnHidden items={[
      { key: "login", label: "登录", disabled: busy, children: <PasswordLogin login={login} onBusyChange={setBusy} /> },
      { key: "register", label: "注册", disabled: busy, children: <Registration onLogin={() => setTab("login")} onBusyChange={setBusy} /> },
      { key: "code-login", label: "验证码登录", disabled: busy, children: <CodeLogin login={login} onBusyChange={setBusy} /> },
      { key: "reset", label: "找回密码", disabled: busy, children: <PasswordReset onLogin={() => setTab("login")} onBusyChange={setBusy} /> },
    ]} />
  </AuthFrame>;
}
