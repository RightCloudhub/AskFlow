/** WebSocket chat client; token rotation authenticates the next connection. */
import { getToken } from "../api/client.ts";
import type { CitationSource } from "../api/types";
import { authenticateSocket } from "./chat-socket-auth.ts";
import { streamMessage } from "./chat-stream.ts";

export type StreamHandlers = {
  onIntent?: (payload: { intent?: string; route?: string; confidence?: number }) => void;
  onSource?: (source: CitationSource) => void;
  onToken?: (chunk: string) => void;
  onHandoff?: (payload: Record<string, unknown>) => void;
  onTicket?: (payload: Record<string, unknown>) => void;
  onEnd?: (payload: StreamEndPayload) => void;
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
function wsUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${WS_PATH}`;
}

export class ChatSocket {
  private socket: WebSocket | null = null;
  private ready: Promise<void> | null = null;
  private token: string | null = null;

  async connect(): Promise<void> {
    if (this.token !== getToken()) this.close();
    if (this.socket?.readyState === WebSocket.OPEN && !this.ready) return;
    if (this.ready) return this.ready;
    const pending = this.open();
    this.ready = pending;
    try { await pending; }
    finally { if (this.ready === pending) this.ready = null; }
  }

  private async open(): Promise<void> {
    const token = getToken();
    if (!token) throw new Error("未登录");
    const socket = new WebSocket(wsUrl());
    this.socket = socket;
    this.token = token;
    socket.addEventListener("close", () => { if (this.socket === socket) this.socket = null; });
    await authenticateSocket(socket, token);
  }

  async sendMessage(conversationId: string, content: string, handlers: StreamHandlers): Promise<void> {
    await this.connect();
    const socket = this.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) throw new Error("WebSocket 未连接");
    return streamMessage(socket, JSON.stringify({ type: "message", conversation_id: conversationId, content }), handlers);
  }

  close() {
    this.socket?.close();
    this.socket = null;
    this.ready = null;
    this.token = null;
  }
}

let shared: ChatSocket | null = null;
export function getChatSocket(): ChatSocket { return shared ??= new ChatSocket(); }
export function disposeChatSocket() { shared?.close(); shared = null; }
