import { Input } from "antd";
import { LockOutlined, MailOutlined, UserOutlined } from "@ant-design/icons";
import type { useLoginForm } from "./use-login-form";

const MIN_USERNAME_LENGTH = 3;
const MIN_PASSWORD_LENGTH = 8;
export function AuthFields({ state }: { state: ReturnType<typeof useLoginForm> }) {
  return <><label className="af-field"><span>用户名</span><Input value={state.username}
    onChange={(event) => state.setUsername(event.target.value)} required minLength={MIN_USERNAME_LENGTH} size="large"
    prefix={<UserOutlined />} placeholder="请输入用户名" autoComplete="username" aria-describedby="af-username-hint" />
    <small id="af-username-hint">至少 {MIN_USERNAME_LENGTH} 个字符</small></label>
    {state.mode === "register" && <label className="af-field"><span>邮箱</span><Input type="email" value={state.email}
      onChange={(event) => state.setEmail(event.target.value)} required size="large" prefix={<MailOutlined />}
      placeholder="name@company.com" autoComplete="email" /></label>}
    <label className="af-field"><span>密码</span><Input.Password value={state.password}
      onChange={(event) => state.setPassword(event.target.value)} required minLength={MIN_PASSWORD_LENGTH} size="large"
      prefix={<LockOutlined />} autoComplete={state.mode === "login" ? "current-password" : "new-password"}
      aria-describedby="af-password-hint" /><small id="af-password-hint">至少 {MIN_PASSWORD_LENGTH} 位</small></label>
  </>;
}
