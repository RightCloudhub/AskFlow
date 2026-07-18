/** WebSocket chat client — progressive token frames from /ws/chat. */

import { getToken } from "../api/client";
import type { CitationSource } from "../api/types";

export type StreamHandlers = {
  onIntent?: (p: { intent?: string; route?: string; confidence?: number }) => void;
  onSource?: (s: CitationSource) => void;
  onToken?: (chunk: string) => void;
  onHandoff?: (p: Record<string, unknown>) => void;
  onTicket?: (p: Record<string, unknown>) => void;
  onEnd?: (p: StreamEndPayload) => void;
  onError?: (message: string) => void;
};

export type StreamEndPayload = {
  message_id?: string;
  user_message_id?: string;
  route?: string;
  intent?: string;
  sources?: CitationSource[];
  answer_confidence?: number;
  refused?: boolean;
  flags?: string[];
  cancelled?: boolean;
};

const WS_PATH = "/api/v1/chat/ws";
const CONNECT_TIMEOUT_MS = 8000;

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${WS_PATH}`;
}

export class ChatSocket {
  private socket: WebSocket | null = null;
  private ready: Promise<void> | null = null;

  async connect(): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN) return;
    if (this.ready) return this.ready;
    this.ready = this._open();
    try {
      await this.ready;
    } finally {
      this.ready = null;
    }
  }

  private _open(): Promise<void> {
    return new Promise((resolve, reject) => {
      const token = getToken();
      if (!token) {
        reject(new Error("未登录"));
        return;
      }
      const ws = new WebSocket(wsUrl());
      this.socket = ws;
      let settled = false;
      const timer = window.setTimeout(() => {
        if (settled) return;
        settled = true;
        reject(new Error("WebSocket 连接超时"));
        ws.close();
      }, CONNECT_TIMEOUT_MS);

      const finish = (err?: Error) => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        if (err) reject(err);
        else resolve();
      };

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: "auth", token }));
      };

      ws.onmessage = (ev) => {
        let frame: { type?: string; message?: string };
        try {
          frame = JSON.parse(String(ev.data)) as { type?: string; message?: string };
        } catch {
          return;
        }
        if (frame.type === "auth_ok") {
          ws.onmessage = null;
          finish();
          return;
        }
        if (frame.type === "error") {
          finish(new Error(frame.message || "认证失败"));
        }
      };

      ws.onerror = () => finish(new Error("WebSocket 连接失败"));

      ws.onclose = () => {
        this.socket = null;
        if (!settled) finish(new Error("WebSocket 已关闭"));
      };
    });
  }

  async sendMessage(
    conversationId: string,
    content: string,
    handlers: StreamHandlers,
  ): Promise<void> {
    await this.connect();
    const ws = this.socket;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket 未连接");
    }

    return new Promise((resolve, reject) => {
      const onMessage = (ev: MessageEvent) => {
        let frame: Record<string, unknown>;
        try {
          frame = JSON.parse(String(ev.data)) as Record<string, unknown>;
        } catch {
          return;
        }
        dispatchFrame(frame, handlers, () => {
          ws.removeEventListener("message", onMessage);
          resolve();
        }, (err) => {
          ws.removeEventListener("message", onMessage);
          reject(err);
        });
      };

      ws.addEventListener("message", onMessage);
      ws.send(
        JSON.stringify({
          type: "message",
          conversation_id: conversationId,
          content,
        }),
      );
    });
  }

  close() {
    this.socket?.close();
    this.socket = null;
  }
}

function dispatchFrame(
  frame: Record<string, unknown>,
  handlers: StreamHandlers,
  onDone: () => void,
  onFail: (e: Error) => void,
) {
  const type = String(frame.type || "");
  if (type === "error") {
    const msg = String(frame.message || "发送失败");
    handlers.onError?.(msg);
    onFail(new Error(msg));
    return;
  }
  if (type === "intent") {
    handlers.onIntent?.({
      intent: frame.intent as string | undefined,
      route: frame.route as string | undefined,
      confidence: frame.confidence as number | undefined,
    });
    return;
  }
  if (type === "source") {
    handlers.onSource?.(frame as CitationSource);
    return;
  }
  if (type === "token") {
    handlers.onToken?.(String(frame.content || ""));
    return;
  }
  if (type === "handoff") {
    handlers.onHandoff?.(frame);
    return;
  }
  if (type === "ticket") {
    handlers.onTicket?.(frame);
    return;
  }
  if (type === "message_end") {
    handlers.onEnd?.(frame as StreamEndPayload);
    onDone();
  }
}

let shared: ChatSocket | null = null;

export function getChatSocket(): ChatSocket {
  if (!shared) shared = new ChatSocket();
  return shared;
}

export function disposeChatSocket() {
  shared?.close();
  shared = null;
}
