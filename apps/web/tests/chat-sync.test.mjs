import assert from "node:assert/strict";
import test from "node:test";
import { setImmediate } from "node:timers/promises";
import { messageSyncOptions, MESSAGE_SYNC_INTERVAL_MS } from "../src/services/message-sync.ts";
import { ChatKeys } from "../src/hooks/query-keys.ts";

// Query timers run in a browser environment; no browser or network is needed here.
globalThis.window = new EventTarget();
const { QueryClient, QueryObserver, focusManager } = await import("@tanstack/query-core");

function observe(t, queryFn) {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  focusManager.setFocused(true);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  client.mount();
  const options = { ...messageSyncOptions, queryKey: ChatKeys.messages("current"), queryFn };
  const observer = new QueryObserver(client, options);
  const unsubscribe = observer.subscribe(() => {});
  t.after(() => { unsubscribe(); client.unmount(); client.clear(); focusManager.setFocused(undefined); });
  return { client, observer, options };
}

test("a saved staff reply arrives without sending a message or reloading", async (t) => {
  const initial = { id: "question", role: "user", content: "请转人工客服" };
  const reply = { id: "reply", role: "staff", content: "您好，我来帮您处理。" };
  let saved = [initial];
  const { observer } = observe(t, async () => [...saved]);
  await observer.refetch();
  assert.deepEqual(observer.getCurrentResult().data, [initial]);
  saved = [initial, reply];
  t.mock.timers.tick(MESSAGE_SYNC_INTERVAL_MS);
  await setImmediate();
  assert.deepEqual(observer.getCurrentResult().data, saved);
  t.mock.timers.tick(MESSAGE_SYNC_INTERVAL_MS);
  await setImmediate();
  assert.equal(observer.getCurrentResult().data.length, saved.length);
});

test("sending cancels an older read and pauses synchronization until the send ends", async (t) => {
  let finishRead;
  let reads = 0;
  const { client, observer, options } = observe(t, ({ signal }) => {
    reads += 1;
    assert.equal(signal.aborted, false);
    return new Promise((resolve) => { finishRead = resolve; });
  });
  observer.setOptions({ ...options, enabled: false });
  await client.cancelQueries({ queryKey: options.queryKey });
  const pending = [{ id: "pending", role: "user", content: "补充信息" }];
  client.setQueryData(options.queryKey, pending);
  finishRead([]);
  t.mock.timers.tick(MESSAGE_SYNC_INTERVAL_MS);
  await setImmediate();
  assert.equal(reads, 1);
  assert.deepEqual(client.getQueryData(options.queryKey), pending);
  observer.setOptions({ ...options, enabled: true });
  finishRead([{ id: "saved", role: "user", content: "补充信息" }]);
  await setImmediate();
  assert.equal(observer.getCurrentResult().data[0].id, "saved");
});

test("hidden pages pause polling and recover automatically on focus and after errors", async (t) => {
  let fail = false;
  let reads = 0;
  const { observer } = observe(t, async () => {
    reads += 1;
    if (fail) throw new Error("offline");
    return [{ id: String(reads), role: "staff", content: "回复" }];
  });
  await observer.refetch();
  const before = reads;
  focusManager.setFocused(false);
  t.mock.timers.tick(MESSAGE_SYNC_INTERVAL_MS);
  await setImmediate();
  assert.equal(reads, before);
  fail = true;
  focusManager.setFocused(true);
  await setImmediate();
  assert.equal(observer.getCurrentResult().isError, true);
  assert.equal(observer.getCurrentResult().data[0].id, String(before));
  fail = false;
  t.mock.timers.tick(MESSAGE_SYNC_INTERVAL_MS);
  await setImmediate();
  assert.equal(observer.getCurrentResult().isSuccess, true);
  assert.ok(reads > before);
});
