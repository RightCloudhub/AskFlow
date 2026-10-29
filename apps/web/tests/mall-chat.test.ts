import assert from "node:assert/strict";
import test from "node:test";
import { setToken } from "../src/api/client.ts";
import { ChatSocket } from "../src/services/chat-ws.ts";

class FakeSocket extends EventTarget {
  static OPEN = 1;
  static instances: FakeSocket[] = [];
  readyState = FakeSocket.OPEN;
  frames: Record<string, unknown>[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(_url: string) {
    super();
    FakeSocket.instances.push(this);
    queueMicrotask(() => this.onopen?.());
  }
  send(payload: string) {
    const frame = JSON.parse(payload);
    this.frames.push(frame);
    if (frame.type === "auth") queueMicrotask(() => this.onmessage?.(new MessageEvent("message", { data: '{"type":"auth_ok"}' })));
  }
  close() { this.readyState = 0; this.dispatchEvent(new Event("close")); }
}

function browser() {
  const values = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value); },
    removeItem: (key: string) => { values.delete(key); },
  } });
  Object.defineProperty(globalThis, "window", { configurable: true, value: Object.assign(new EventTarget(), {
    location: { protocol: "http:", host: "localhost" }, setTimeout, clearTimeout,
  }) });
  Object.defineProperty(globalThis, "WebSocket", { configurable: true, value: FakeSocket });
  FakeSocket.instances = [];
}

test("an HTTP token rotation makes the next chat connection authenticate again", async () => {
  browser();
  setToken("original");
  const socket = new ChatSocket();
  await socket.connect();
  setToken("renewed", { renewal: true });
  await socket.connect();
  const [original, renewed] = FakeSocket.instances;
  assert.equal(original.readyState, 0);
  assert.deepEqual(renewed.frames, [{ type: "auth", token: "renewed" }]);
  socket.close();
});

test("a closed stream rejects so the composer can stop waiting", async () => {
  browser();
  setToken("original");
  const socket = new ChatSocket();
  await socket.connect();
  const connection = FakeSocket.instances[0];
  const pending = socket.sendMessage("conversation", "message", {});
  const rejected = assert.rejects(pending, /连接已中断/);
  await new Promise<void>((resolve) => setTimeout(resolve, 0));
  connection.close();
  await rejected;
});
