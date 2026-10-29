import assert from "node:assert/strict";
import test from "node:test";
import { api, getToken, setToken, setUnauthorizedRecovery } from "../src/api/client.ts";
import { prepareMallSession, refreshMallSession } from "../src/mall/session.ts";
import { mall } from "../src/mall/client.ts";

function browser() {
  const storage = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => { storage.set(key, value); },
    removeItem: (key: string) => { storage.delete(key); },
  } });
  Object.defineProperty(globalThis, "document", { configurable: true,
    value: { cookie: "mall_csrf=fixture-csrf" } });
}

test("parallel consumers rotate the refresh cookie once", async (context) => {
  browser();
  let calls = 0;
  context.mock.method(globalThis, "fetch", async (_url, options) => {
    calls += 1;
    const headers = new Headers(options?.headers);
    assert.equal(headers.get("X-CSRF-Token"), "fixture-csrf");
    assert.equal(options?.credentials, "include");
    return Response.json({ access_token: "rotated" });
  });
  const results = await Promise.all(Array.from({ length: 10 }, () => refreshMallSession()));
  assert.ok(results.every(Boolean));
  assert.equal(calls, 1);
  assert.equal(getToken(), "rotated");
});

test("customer-service requests recover through the mall refresh family", async (context) => {
  browser();
  setToken("expired");
  setUnauthorizedRecovery(refreshMallSession);
  context.after(() => setUnauthorizedRecovery(null));
  context.mock.method(globalThis, "fetch", async (url, options) => {
    if (String(url).endsWith("/account/refresh")) return Response.json({ access_token: "new" });
    const auth = new Headers(options?.headers).get("Authorization");
    return auth === "Bearer new" ? Response.json({ id: "customer" }) : new Response("", { status: 401 });
  });
  assert.deepEqual(await api("/api/v1/admin/auth/me"), { id: "customer" });
  assert.equal(getToken(), "new");
});

test("chat preparation refuses a revoked refresh family", async (context) => {
  browser();
  setToken("header." + btoa(JSON.stringify({ exp: 1 })) + ".signature");
  context.mock.method(globalThis, "fetch", async () => new Response("", { status: 401 }));
  await assert.rejects(prepareMallSession(), /会话已过期/);
  assert.equal(getToken(), null);
});

test("mall and customer-service clients share a single refresh", async (context) => {
  browser();
  setToken("expired");
  setUnauthorizedRecovery(refreshMallSession);
  context.after(() => setUnauthorizedRecovery(null));
  let rotations = 0;
  context.mock.method(globalThis, "fetch", async (url, options) => {
    if (String(url).endsWith("/account/refresh")) {
      rotations += 1;
      return Response.json({ access_token: "new" });
    }
    return new Headers(options?.headers).get("Authorization") === "Bearer new" ?
      Response.json({ status: "ok" }) : new Response("", { status: 401 });
  });
  const results = await Promise.all([api("/api/v1/chat/conversations"), mall("/account/profile")]);
  assert.deepEqual(results, [{ status: "ok" }, { status: "ok" }]);
  assert.equal(rotations, 1);
});

test("a late expired response reuses the token already rotated by another request", async (context) => {
  browser();
  setToken("expired");
  setUnauthorizedRecovery(refreshMallSession);
  context.after(() => setUnauthorizedRecovery(null));
  let release!: (response: Response) => void;
  const late = new Promise<Response>((resolve) => { release = resolve; });
  let rotations = 0;
  context.mock.method(globalThis, "fetch", async (url, options) => {
    if (String(url).endsWith("/account/refresh")) {
      rotations += 1;
      return Response.json({ access_token: "new" });
    }
    if (new Headers(options?.headers).get("Authorization") === "Bearer new") return Response.json({ ok: true });
    if (String(url).includes("profile")) return late;
    return new Response("", { status: 401 });
  });
  const original = api("/api/v1/chat/conversations");
  const delayed = mall("/account/profile");
  await original;
  release(new Response("", { status: 401 }));
  assert.deepEqual(await delayed, { ok: true });
  assert.equal(rotations, 1);
});

test("a refresh finishing after logout cannot restore the old session", async (context) => {
  browser();
  setToken("old");
  let release!: (response: Response) => void;
  context.mock.method(globalThis, "fetch", () => new Promise<Response>((resolve) => { release = resolve; }));
  const pending = refreshMallSession();
  setToken(null);
  release(Response.json({ access_token: "old-renewed" }));
  assert.equal(await pending, false);
  assert.equal(getToken(), null);
});

test("a response belonging to the previous account is discarded", async (context) => {
  browser();
  setToken("customer-a");
  let release!: (response: Response) => void;
  context.mock.method(globalThis, "fetch", () => new Promise<Response>((resolve) => { release = resolve; }));
  const pending = mall("/account/profile");
  setToken("customer-b");
  release(Response.json({ username: "customer-a" }));
  await assert.rejects(pending, /会话已更改/);
  assert.equal(getToken(), "customer-b");
});
