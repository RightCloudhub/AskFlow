import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../../api/client";

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
        await api("/api/v1/admin/auth/register", {
          method: "POST",
          body: JSON.stringify({ username, email, password }),
        });
      }
      const tokenRes = await api<{ access_token: string }>("/api/v1/admin/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
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
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="brand">
          <span className="brand-mark">AF</span>
          <div>
            <h1>AskFlow</h1>
            <p>企业智能客服 · 登录后开始提问</p>
          </div>
        </div>

        <label>
          用户名
          <input value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} />
        </label>
        {mode === "register" && (
          <label>
            邮箱
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
        )}
        <label>
          密码
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
        </label>

        {error && <div className="error-banner">{error}</div>}

        <button type="submit" disabled={loading}>
          {loading ? "处理中…" : mode === "login" ? "登录" : "注册并登录"}
        </button>

        <button
          type="button"
          className="linkish"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "没有账号？注册" : "已有账号？登录"}
        </button>
      </form>
    </div>
  );
}
