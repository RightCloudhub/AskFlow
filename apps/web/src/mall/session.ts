import { getSessionVersion, getToken, setToken } from "../api/client.ts";

const REFRESH_URL = "/api/v1/mall/account/refresh";
const MILLISECONDS_PER_SECOND = 1000;
const RENEW_BEFORE_SECONDS = 30;
let refreshing: Promise<boolean> | null = null;

async function rotate(): Promise<boolean> {
  const version = getSessionVersion();
  const token = getToken();
  const csrf = document.cookie.split("; ").find((part) => part.startsWith("mall_csrf="))?.split("=")[1];
  if (!csrf) return false;
  const response = await fetch(REFRESH_URL, {
    method: "POST", credentials: "include", body: "{}",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(csrf) },
  });
  if (!response.ok) return false;
  const data: { access_token: string } = await response.json();
  if (version !== getSessionVersion() || token !== getToken()) return false;
  if (typeof data.access_token !== "string" || !data.access_token) return false;
  setToken(data.access_token, { renewal: true });
  return true;
}

async function coordinatedRotation(): Promise<boolean> {
  const token = getToken();
  const version = getSessionVersion();
  if (typeof navigator === "undefined" || !navigator.locks) return rotate();
  return navigator.locks.request("askflow-mall-refresh", async () => {
    if (version !== getSessionVersion()) return false;
    if (token !== getToken()) return Boolean(getToken());
    return rotate();
  });
}

/** One rotation shared by mall pages and the original customer-service client. */
export function refreshMallSession(): Promise<boolean> {
  refreshing ??= coordinatedRotation().finally(() => { refreshing = null; });
  return refreshing;
}

export async function logoutMallSession(): Promise<void> {
  const version = getSessionVersion();
  const send = () => fetch("/api/v1/mall/account/logout", { method: "POST", credentials: "include",
    headers: { Authorization: `Bearer ${getToken()}` } });
  try {
    if (refreshing) await refreshing;
    if (version !== getSessionVersion()) return;
    const response = await send();
    if (response.status === 401 && await refreshMallSession() && version === getSessionVersion()) await send();
  } catch { /* Local logout still completes when the network is unavailable. */ }
  finally { if (version === getSessionVersion()) setToken(null); }
}

/** Decoding only schedules renewal; authorization is always checked by the server. */
export async function prepareMallSession(): Promise<void> {
  const token = getToken();
  if (!token) return;
  let expiry = 0;
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const claims: { exp?: number } = JSON.parse(atob(payload));
    expiry = claims.exp ?? 0;
  } catch { return; }
  if (expiry > Date.now() / MILLISECONDS_PER_SECOND + RENEW_BEFORE_SECONDS) return;
  if (!await refreshMallSession()) {
    if (getToken() === token) setToken(null);
    throw new Error("会话已过期，请重新登录");
  }
}
