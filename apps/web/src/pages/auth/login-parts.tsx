import { Input } from "antd";
import { LockOutlined, MailOutlined, UserOutlined } from "@ant-design/icons";
import { BrandMark } from "../../components/layout/BrandMark";
import type { useLoginForm } from "./use-login-form";

const MIN_USERNAME_LENGTH = 3;
const MIN_PASSWORD_LENGTH = 8;
const HIGHLIGHTS = [
  { title: "有依据地回答", desc: "混合检索企业知识库，证据不足时主动拒答，答案附引用。" },
  { title: "人机协作", desc: "工单、暖转人工与 SLA 跟踪，服务任务可追踪、可恢复。" },
  { title: "多渠道接入", desc: "Web、Widget、飞书、企业微信与钉钉共用一套能力。" },
];

export function AuthIntro() {
  return <aside className="af-auth-hero">
    <div className="af-auth-hero-brand"><BrandMark /><strong>AskFlow</strong></div>
    <div className="af-auth-hero-copy"><h2>有依据的企业客服</h2>
      <p>面向企业私有化部署，让每一个服务任务都可跟踪、可恢复。</p>
      <ul className="af-auth-points">{HIGHLIGHTS.map((item) => <li key={item.title}>
        <strong>{item.title}</strong><span>{item.desc}</span>
      </li>)}</ul>
    </div><span className="af-auth-hero-foot">AskFlow · 企业智能客服平台</span>
  </aside>;
}

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
