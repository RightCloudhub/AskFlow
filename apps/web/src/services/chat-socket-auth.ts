const CONNECT_TIMEOUT_MS = 8000;

export function authenticateSocket(socket: WebSocket, token: string): Promise<void> {
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      socket.onmessage = null;
      socket.onerror = null;
      socket.removeEventListener("close", closed);
      if (error) { reject(error); socket.close(); }
      else resolve();
    };
    const closed = () => finish(new Error("WebSocket 已关闭"));
    const timer = window.setTimeout(() => finish(new Error("WebSocket 连接超时")), CONNECT_TIMEOUT_MS);
    socket.addEventListener("close", closed);
    socket.onopen = () => socket.send(JSON.stringify({ type: "auth", token }));
    socket.onerror = () => finish(new Error("WebSocket 连接失败"));
    socket.onmessage = (event) => {
      let frame: { type?: string; message?: string };
      try { frame = JSON.parse(String(event.data)); } catch { return; }
      if (frame.type === "auth_ok") finish();
      if (frame.type === "error") finish(new Error(frame.message || "认证失败"));
    };
  });
}
