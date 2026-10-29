import { assertSession, getSessionVersion, getToken, setToken } from "../api/client.ts";
import { refreshMallSession } from "./session.ts";

const PREFIX = "/api/v1/mall";
const UNAUTHORIZED = 401;
const AUTH_ENDPOINTS = new Set(["login", "register", "refresh", "oidc-session", "verification"]);

function isAuthentication(path: string) {
  const endpoint = path.split("/account/")[1]?.split(/[/?]/)[0];
  return endpoint !== undefined && AUTH_ENDPOINTS.has(endpoint);
}

export async function mall<T>(path: string, options: RequestInit = {}): Promise<T> {
  const version = getSessionVersion();
  const token = getToken();
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const url = path.startsWith("/api/") ? path : PREFIX + path;
  const send = () => fetch(url, { ...options, headers, credentials: "include" });
  const response = await recoverRequest({ path, token, version, headers, send });
  if (response.status === 204) return undefined as T;
  const data = await response.json();
  assertSession(version);
  if (!response.ok) throw new Error(data.message || data.detail || "请求失败，请稍后重试");
  return data as T;
}

type RecoveryRequest = { path: string; token: string | null; version: number; headers: Headers;
  send: () => Promise<Response> };

async function recoverRequest({ path, token, version, headers, send }: RecoveryRequest) {
  let response = await send();
  assertSession(version);
  if (response.status === UNAUTHORIZED && token && !isAuthentication(path)) {
    const recovered = token !== getToken() || await refreshMallSession();
    assertSession(version);
    if (recovered) {
      headers.set("Authorization", `Bearer ${getToken()}`);
      response = await send();
      assertSession(version);
    }
    if (response.status === UNAUTHORIZED) setToken(null);
  }
  return response;
}

export function write<T>(path: string, body: unknown, options: { method?: string; key?: string } = {}) {
  return mall<T>(path, { method: options.method ?? "POST", body: JSON.stringify(body),
    headers: { "Idempotency-Key": options.key ?? crypto.randomUUID() } });
}

const CENTS = 100;
export function money(value: number, currency = "CNY") {
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency }).format(value / CENTS);
}
