const API = "/api/v1";
const STORAGE_KEY = "askflow_widget_session";
export const WIDGET_AUTH_FAILURES = new Set([401, 403]);

export type WidgetSession = { access_token: string; conversation_id: string; visitor_key: string };
export type WidgetMessage = {
  id: string; role: string; content: string; meta?: Record<string, unknown>; failed?: boolean;
};
let pendingSession: Promise<WidgetSession> | undefined;
let memorySession: WidgetSession | undefined;

export class WidgetRequestError extends Error {
  status: number;
  constructor(status: number) { super(`客服请求未完成（${status}），请稍后重试。`); this.status = status; }
}

export async function widgetFetch<T>(path: string, opts: RequestInit & { token?: string } = {}): Promise<T> {
  const headers = new Headers(opts.headers);
  headers.set("Content-Type", "application/json");
  if (opts.token) headers.set("Authorization", `Bearer ${opts.token}`);
  const response = await fetch(`${API}${path}`, { ...opts, headers });
  if (!response.ok) throw new WidgetRequestError(response.status);
  return response.json() as Promise<T>;
}

function storedSession(): WidgetSession | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    const session = raw ? JSON.parse(raw) as Partial<WidgetSession> : null;
    if (session && typeof session.access_token === "string" && typeof session.conversation_id === "string"
      && typeof session.visitor_key === "string") return session as WidgetSession;
  } catch { /* The widget also works when browser storage is unavailable. */ }
  return null;
}

export function clearWidgetSession() {
  memorySession = undefined;
  try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* Storage is optional. */ }
}

export async function getWidgetSession(): Promise<WidgetSession> {
  const stored = storedSession() ?? memorySession;
  if (stored) return stored;
  if (!pendingSession) pendingSession = widgetFetch<WidgetSession>("/widget/session", {
    method: "POST", body: JSON.stringify({ title: "官网咨询", origin: window.location.origin }),
  });
  try {
    const session = await pendingSession;
    memorySession = session;
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session)); } catch { /* Continue with the in-memory session. */ }
    return session;
  } finally { pendingSession = undefined; }
}
