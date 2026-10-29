export const TOKEN_KEY = "askflow_token";
/** Fired whenever the session token changes (login / logout). */
export const AUTH_EVENT = "askflow:auth";
export const SESSION_EVENT = "askflow:session";
const UNAUTHORIZED = 401;
let sessionVersion = 0;
let unauthorizedRecovery: (() => Promise<boolean>) | null = null;

/** Optional profile-specific recovery; absent in the original profiles. */
export function setUnauthorizedRecovery(handler: (() => Promise<boolean>) | null) {
  unauthorizedRecovery = handler;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getSessionVersion() { return sessionVersion; }

export function assertSession(version: number) {
  if (version !== sessionVersion) throw new Error("会话已更改，请重新操作");
}

export function synchronizeSession() {
  sessionVersion += 1;
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(SESSION_EVENT));
    window.dispatchEvent(new Event(AUTH_EVENT));
  }
}

export function setToken(token: string | null, options: { renewal?: boolean } = {}) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
  if (!options.renewal) synchronizeSession();
  else if (typeof window !== "undefined") window.dispatchEvent(new Event(AUTH_EVENT));
}

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string, statusText: string) {
    super(body || statusText || `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function authHeaders(extra?: HeadersInit, json = true): Headers {
  const headers = new Headers(extra);
  if (json && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return headers;
}

function redirectOnUnauthorized(status: number) {
  if (status !== UNAUTHORIZED) return;
  setToken(null);
  if (typeof window === "undefined") return;
  if (window.location.pathname === "/login") return;
  if (window.location.pathname.startsWith("/widget")) return;
  window.location.assign("/login");
}

async function parseError(res: Response): Promise<ApiError> {
  const text = await res.text();
  return new ApiError(res.status, text, res.statusText);
}

async function request(path: string, options: RequestInit, json: boolean) {
  const version = getSessionVersion();
  const token = getToken();
  const send = () => fetch(path, { ...options, headers: authHeaders(options.headers, json) });
  const response = await send();
  assertSession(version);
  if (response.status !== UNAUTHORIZED || !token || !unauthorizedRecovery) return response;
  if (/\/auth\/(login|register)$/.test(path)) return response;
  const recovered = token !== getToken() || await unauthorizedRecovery();
  assertSession(version);
  if (!recovered) return response;
  const retried = await send();
  assertSession(version);
  return retried;
}

/** JSON request helper — single HTTP entry (RAGFlow-style layering base). */
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const version = getSessionVersion();
  const res = await request(path, options, true);
  if (!res.ok) {
    redirectOnUnauthorized(res.status);
    throw await parseError(res);
  }
  if (res.status === 204) return undefined as T;
  const data: T = await res.json();
  assertSession(version);
  return data;
}

/** Multipart / binary upload (no forced Content-Type). */
export async function apiForm<T>(
  path: string,
  form: FormData,
  options: RequestInit = {},
): Promise<T> {
  const version = getSessionVersion();
  const res = await request(path, {
    ...options,
    method: options.method ?? "POST",
    body: form,
  }, false);
  if (!res.ok) {
    redirectOnUnauthorized(res.status);
    throw await parseError(res);
  }
  const data: T = await res.json();
  assertSession(version);
  return data;
}

export type {
  User,
  Conversation,
  Message,
  CitationSource,
  DocumentRow,
  Ticket,
  AnalyticsSummary,
  SendMessageResult,
} from "./types";
