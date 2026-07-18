const TOKEN_KEY = "askflow_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
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
  if (status !== 401) return;
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

/** JSON request helper — single HTTP entry (RAGFlow-style layering base). */
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: authHeaders(options.headers, true),
  });
  if (!res.ok) {
    redirectOnUnauthorized(res.status);
    throw await parseError(res);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Multipart / binary upload (no forced Content-Type). */
export async function apiForm<T>(
  path: string,
  form: FormData,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(path, {
    ...options,
    method: options.method ?? "POST",
    headers: authHeaders(options.headers, false),
    body: form,
  });
  if (!res.ok) {
    redirectOnUnauthorized(res.status);
    throw await parseError(res);
  }
  return res.json() as Promise<T>;
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
