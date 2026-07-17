const TOKEN_KEY = "askflow_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type User = {
  id: string;
  username: string;
  email: string;
  role: string;
};

export type Conversation = {
  id: string;
  title: string;
  status: string;
};

export type Message = {
  id: string;
  role: string;
  content: string;
  meta?: Record<string, unknown>;
  created_at: string;
};
