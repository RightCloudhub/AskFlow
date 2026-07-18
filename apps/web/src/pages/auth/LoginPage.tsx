import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Card, Input, Typography } from "antd";
import { setToken } from "../../api/client";
import { authService } from "../../services/auth-service";

const { Title, Text } = Typography;

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
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <Card className="auth-card-antd" bordered={false}>
        <form onSubmit={(e) => void onSubmit(e)} className="af-login-form">
          <div className="brand">
            <span className="brand-mark">AF</span>
            <div>
              <Title level={3} style={{ margin: 0 }}>
                AskFlow
              </Title>
              <Text type="secondary">企业智能客服 · 登录后开始提问</Text>
            </div>
          </div>

          <label className="af-field">
            <span>用户名</span>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              size="large"
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
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
            />
          </label>

          {error ? <Alert type="error" showIcon message={error} /> : null}

          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            loading={loading}
          >
            {mode === "login" ? "登录" : "注册并登录"}
          </Button>

          <Button
            type="link"
            block
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "没有账号？注册" : "已有账号？登录"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
