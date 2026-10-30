import assert from "node:assert/strict";
import test from "node:test";
import { clearWidgetSession, getWidgetSession, widgetFetch, WidgetRequestError } from "../src/pages/widget/widget-service.ts";

const SESSION = { access_token: "widget-fixture-token", conversation_id: "fixture-conversation", visitor_key: "fixture-visitor" };

function storage(blocked = false) {
  const values = new Map<string, string>();
  Object.defineProperty(globalThis, "sessionStorage", { configurable: true, value: {
    getItem: (key: string) => { if (blocked) throw new Error("Storage unavailable"); return values.get(key) ?? null; },
    setItem: (key: string, value: string) => { if (blocked) throw new Error("Storage unavailable"); values.set(key, value); },
    removeItem: (key: string) => values.delete(key),
  } });
  Object.defineProperty(globalThis, "window", { configurable: true, value: { location: { origin: "https://fixture.invalid" } } });
  clearWidgetSession();
}

test("overlapping widget mounts share one session and retain the same conversation", async (context) => {
  storage();
  let requests = 0;
  context.mock.method(globalThis, "fetch", async () => {
    requests += 1;
    return Response.json(SESSION);
  });
  const [first, second] = await Promise.all([getWidgetSession(), getWidgetSession()]);
  assert.deepEqual(first, SESSION);
  assert.deepEqual(second, SESSION);
  await getWidgetSession();
  assert.equal(requests, 1);
});

test("a browser that denies storage can reconnect to the in-memory conversation", async (context) => {
  storage(true);
  let requests = 0;
  context.mock.method(globalThis, "fetch", async () => { requests += 1; return Response.json(SESSION); });
  await getWidgetSession();
  await getWidgetSession();
  assert.equal(requests, 1);
});

test("failed creation can be retried without keeping a rejected session promise", async (context) => {
  storage();
  let requests = 0;
  context.mock.method(globalThis, "fetch", async () => {
    requests += 1;
    if (requests === 1) throw new TypeError("Failed to fetch");
    return Response.json(SESSION);
  });
  await assert.rejects(getWidgetSession(), /Failed to fetch/);
  assert.deepEqual(await getWidgetSession(), SESSION);
});

test("widget requests carry authentication and expose an HTTP failure without response internals", async (context) => {
  let sent: Headers | undefined;
  context.mock.method(globalThis, "fetch", async (_url, options) => {
    sent = new Headers(options?.headers);
    return new Response("private server details", { status: 401 });
  });
  await assert.rejects(widgetFetch("/widget/history", { token: SESSION.access_token }), (error: unknown) => {
    assert.ok(error instanceof WidgetRequestError);
    assert.equal(error.status, 401);
    assert.doesNotMatch(error.message, /private server/);
    return true;
  });
  assert.equal(sent?.get("Authorization"), `Bearer ${SESSION.access_token}`);
});
