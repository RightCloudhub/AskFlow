import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Input, Segmented, Typography } from "antd";
import {
  ApiOutlined,
  LockOutlined,
  MailOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { setToken } from "../../api/client";
import { authService } from "../../services/auth-service";

const { Title, Text } = Typography;

const HIGHLIGHTS = [
  {
    icon: <SafetyCertificateOutlined />,
    title: "有依据地回答",
    desc: "混合检索企业知识库，证据不足时主动拒答，答案附引用。",
  },
  {
    icon: <TeamOutlined />,
    title: "人机协作",
    desc: "工单、暖转人工与 SLA 跟踪，服务任务可追踪、可恢复。",
  },
  {
    icon: <ApiOutlined />,
    title: "多渠道接入",
    desc: "Web、嵌入式 Widget、飞书、企业微信与钉钉共用一套能力。",
  },
];

const KNOWN_ERRORS: Array<[string, string]> = [
  ["Invalid username or password", "用户名或密码错误"],
  ["User is inactive", "该账号已被禁用，请联系管理员"],
  ["already registered", "用户名或邮箱已被注册"],
  [
    "Local registration disabled",
    "当前环境未开放自助注册，请使用企业 SSO 登录",
  ],
];

function readError(err: unknown, mode: "login" | "register"): string {
  let raw = err instanceof Error ? err.message : "";
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    if (typeof parsed.detail === "string") raw = parsed.detail;
  } catch {
    /* not JSON */
  }
  const hit = KNOWN_ERRORS.find(([needle]) => raw.includes(needle));
  if (hit) return hit[1];
  return (
    raw || (mode === "login" ? "登录失败，请稍后重试" : "注册失败，请稍后重试")
  );
}

export function LoginPage() {
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        await authService.register(username, email, password);
      }
      const tokenRes = await authService.login(username, password);
      setToken(tokenRes.access_token);
      nav("/");
    } catch (err) {
      setError(readError(err, mode));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="af-auth">
      <aside className="af-auth-hero">
        <div className="af-auth-hero-brand">
          <span className="brand-mark">AF</span>
          <strong>AskFlow</strong>
        </div>
        <div className="af-auth-hero-copy">
          <h1>面向企业私有化部署的智能客服</h1>
          <p>有依据地回答，让每一个服务任务都可跟踪、可恢复。</p>
          <ul className="af-auth-points">
            {HIGHLIGHTS.map((h) => (
              <li key={h.title}>
                <span className="af-auth-point-icon">{h.icon}</span>
                <div>
                  <strong>{h.title}</strong>
                  <span>{h.desc}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <span className="af-auth-hero-foot">© AskFlow · 企业智能客服平台</span>
      </aside>

      <main className="af-auth-main">
        <form onSubmit={(e) => void onSubmit(e)} className="af-auth-form">
          <div className="af-auth-mobile-brand">
            <span className="brand-mark sm">AF</span>
            <strong>AskFlow</strong>
          </div>
          <div>
            <Title level={3} className="af-auth-title">
              {mode === "login" ? "欢迎回来" : "创建账号"}
            </Title>
            <Text type="secondary">
              {mode === "login"
                ? "登录后即可开始咨询或进入管理控制台"
                : "注册后将自动登录"}
            </Text>
          </div>

          <Segmented
            block
            value={mode}
            onChange={(v) => {
              setMode(v as "login" | "register");
              setError(null);
            }}
            options={[
              { label: "登录", value: "login" },
              { label: "注册", value: "register" },
            ]}
          />

          <label className="af-field">
            <span>用户名</span>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              size="large"
              prefix={<UserOutlined />}
              placeholder="请输入用户名"
              autoComplete="username"
            />
          </label>

          {mode === "register" ? (
            <label className="af-field">
              <span>邮箱</span>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                size="large"
                prefix={<MailOutlined />}
                placeholder="name@company.com"
                autoComplete="email"
              />
            </label>
          ) : null}

          <label className="af-field">
            <span>密码</span>
            <Input.Password
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              size="large"
              prefix={<LockOutlined />}
              placeholder="至少 8 位"
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
            />
          </label>

          {error ? <Alert type="error" showIcon title={error} /> : null}

          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            loading={loading}
          >
            {mode === "login" ? "登录" : "注册并登录"}
          </Button>
        </form>
      </main>
    </div>
  );
}
