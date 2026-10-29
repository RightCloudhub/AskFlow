import type { CitationSource } from "../api/types";
import type { StreamEndPayload, StreamHandlers } from "./chat-ws";

const STREAM_TIMEOUT_MS = 60000;
type Completion = { handlers: StreamHandlers; done: () => void; fail: (error: Error) => void };

function dispatchFrame(frame: Record<string, unknown>, completion: Completion) {
  const { handlers, done, fail } = completion;
  const type = String(frame.type || "");
  const actions: Record<string, () => void> = {
    error: () => {
      const message = String(frame.message || "发送失败");
      handlers.onError?.(message);
      fail(new Error(message));
    },
    intent: () => handlers.onIntent?.({ intent: frame.intent as string | undefined,
      route: frame.route as string | undefined, confidence: frame.confidence as number | undefined }),
    source: () => handlers.onSource?.(frame as CitationSource),
    token: () => handlers.onToken?.(String(frame.content || "")),
    handoff: () => handlers.onHandoff?.(frame),
    ticket: () => handlers.onTicket?.(frame),
    message_end: () => { handlers.onEnd?.(frame as StreamEndPayload); done(); },
  };
  actions[type]?.();
}

export function streamMessage(socket: WebSocket, payload: string, handlers: StreamHandlers): Promise<void> {
  return new Promise((resolve, reject) => {
    const finish = (error?: Error) => {
      window.clearTimeout(timer);
      socket.removeEventListener("message", received);
      socket.removeEventListener("close", closed);
      if (error) reject(error); else resolve();
    };
    const closed = () => finish(new Error("连接已中断，请刷新消息确认发送结果"));
    const received = (event: MessageEvent) => {
      let frame: Record<string, unknown>;
      try { frame = JSON.parse(String(event.data)); } catch { return; }
      dispatchFrame(frame, { handlers, done: () => finish(), fail: finish });
    };
    const timer = window.setTimeout(() => {
      finish(new Error("等待回复超时，请刷新消息确认发送结果"));
      socket.close();
    }, STREAM_TIMEOUT_MS);
    socket.addEventListener("message", received);
    socket.addEventListener("close", closed);
    try { socket.send(payload); } catch (error) { finish(error instanceof Error ? error : new Error("发送失败")); }
  });
}
