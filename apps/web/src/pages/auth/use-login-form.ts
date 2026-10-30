import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { setToken } from "../../api/client";
import { authService } from "../../services/auth-service";

const KNOWN_ERRORS: Array<[string, string]> = [
  ["Invalid username or password", "用户名或密码错误"],
  ["User is inactive", "该账号已被禁用，请联系管理员"],
  ["already registered", "用户名或邮箱已被注册"],
  ["Local registration disabled", "当前环境未开放自助注册，请使用企业 SSO 登录"],
];

function readError(error: unknown, mode: "login" | "register") {
  let raw = error instanceof Error ? error.message : "";
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    if (typeof parsed.detail === "string") raw = parsed.detail;
  } catch { /* Plain text errors remain readable. */ }
  const known = KNOWN_ERRORS.find(([needle]) => raw.includes(needle));
  return known?.[1] ?? (raw || (mode === "login" ? "登录失败，请稍后重试" : "注册失败，请稍后重试"));
}

export function useLoginForm() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null); setLoading(true);
    try {
      if (mode === "register") await authService.register(username, email, password);
      const token = await authService.login(username, password);
      setToken(token.access_token); navigate("/");
    } catch (reason) { setError(readError(reason, mode)); }
    finally { setLoading(false); }
  }
  return { username, setUsername, password, setPassword, email, setEmail, mode, setMode, error, setError, loading, submit };
}
