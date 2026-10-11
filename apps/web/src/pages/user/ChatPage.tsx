import { useEffect, useRef, useState } from "react";
import { Alert, Spin } from "antd";
import { useNavigate } from "react-router-dom";
import { setToken } from "../../api/client";
import type { CitationSource, Message } from "../../api/types";
import {
  Composer,
  HandoffBanner,
  MessageList,
  SourcePanel,
} from "../../components/chat";
import { AppShell } from "../../components/layout/AppShell";
import { useMe } from "../../hooks/use-auth";
import {
  useConversations,
  useCreateConversation,
  useMessages,
} from "../../hooks/use-chat";
import { getChatSocket } from "../../services/chat-ws";
import { useQueryClient } from "@tanstack/react-query";
import { ChatKeys } from "../../hooks/query-keys";

export function ChatPage() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [streamText, setStreamText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [handoffHint, setHandoffHint] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const meQ = useMe();
  const convQ = useConversations(meQ.isSuccess);
  const msgQ = useMessages(activeId);
  const createConv = useCreateConversation();

  useEffect(() => {
    if (meQ.isError) {
      setToken(null);
      nav("/login");
    }
  }, [meQ.isError, nav]);

  useEffect(() => {
    if (!activeId && convQ.data?.[0]) setActiveId(convQ.data[0].id);
  }, [activeId, convQ.data]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgQ.data, streamText, streaming]);

  async function handleNewChat() {
    const conv = await createConv.mutateAsync("新会话");
    setActiveId(conv.id);
    setHandoffHint(null);
  }

  async function handleSuggest(content: string) {
    if (streaming) return;
    let convId = activeId;
    if (!convId) {
      const conv = await createConv.mutateAsync(content.slice(0, 20));
      convId = conv.id;
      setActiveId(conv.id);
    }
    await handleSend(content, convId);
  }

  async function handleSend(content: string, convId: string | null = activeId) {
    if (!convId || streaming) return;
    const activeId = convId;
    setSendError(null);
    setStreaming(true);
    setStreamText("");
    const sources: CitationSource[] = [];
    let endMeta: Record<string, unknown> = {};

    // Optimistic user bubble via cache
    const tempUser: Message = {
      id: `tmp-u-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    const key = ChatKeys.messages(activeId);
    const prev = qc.getQueryData<Message[]>(key) ?? [];
    qc.setQueryData<Message[]>(key, [...prev, tempUser]);

    try {
      await getChatSocket().sendMessage(activeId, content, {
        onToken: (chunk) => setStreamText((t) => t + chunk),
        onSource: (s) => sources.push(s),
        onHandoff: (p) =>
          setHandoffHint(String(p.summary || "已进入人工接管队列")),
        onEnd: (p) => {
          endMeta = {
            route: p.route,
            answer_confidence: p.answer_confidence,
            refused: p.refused,
            sources: p.sources?.length ? p.sources : sources,
          };
        },
        onError: (m) => setSendError(m),
      });
      await qc.invalidateQueries({ queryKey: key });
      await qc.invalidateQueries({ queryKey: ChatKeys.conversations() });
      // if stream leftover and invalidate slow, still clear
      void endMeta;
    } catch (e) {
      setSendError(e instanceof Error ? e.message : "发送失败");
      qc.setQueryData<Message[]>(key, prev);
    } finally {
      setStreaming(false);
      setStreamText("");
    }
  }

  const activeConv = convQ.data?.find((c) => c.id === activeId);
  const isHandoff =
    activeConv?.status === "transferred" || Boolean(handoffHint);

  const loadingShell = meQ.isLoading || (meQ.isSuccess && convQ.isLoading);

  if (loadingShell) {
    return (
      <div className="af-query-state" style={{ minHeight: "100vh" }}>
        <Spin size="large" description="加载会话…">
          <div style={{ width: 120, height: 60 }} />
        </Spin>
      </div>
    );
  }

  return (
    <AppShell
      me={meQ.data}
      conversations={convQ.data ?? []}
      activeId={activeId}
      onSelectConversation={(id) => {
        setActiveId(id);
        setHandoffHint(null);
      }}
      onNewChat={() => void handleNewChat()}
      creating={createConv.isPending}
      title={activeConv?.title || "智能客服"}
      subtitle={
        isHandoff
          ? "已转接人工客服，座席认领后将继续为您服务"
          : "基于企业知识库作答，可随时转人工"
      }
    >
      <div className="af-chat-stage">
        {handoffHint ? (
          <div className="af-chat-banner">
            <HandoffBanner
              summary={handoffHint}
              onGoAdmin={
                meQ.data?.role && meQ.data.role !== "user"
                  ? () => nav("/admin/handoffs")
                  : undefined
              }
            />
          </div>
        ) : null}
        {msgQ.isLoading && activeId && !streaming ? (
          <div className="af-query-state">
            <Spin description="加载消息…">
              <div style={{ width: 120, height: 60 }} />
            </Spin>
          </div>
        ) : (
          <MessageList
            messages={msgQ.data ?? []}
            streaming={streaming}
            streamingText={streamText}
            onSuggest={(t) => void handleSuggest(t)}
          />
        )}
        <div ref={bottomRef} />
      </div>

      {sendError ? (
        <div className="af-chat-error">
          <Alert
            type="error"
            showIcon
            closable
            onClose={() => setSendError(null)}
            title="消息发送失败"
            description={sendError}
          />
        </div>
      ) : null}

      <Composer
        disabled={!activeId}
        sending={streaming}
        placeholder={
          activeId ? undefined : "请先新建会话，或点击上方的常见问题"
        }
        onSend={handleSend}
      />
      <SourcePanel />
    </AppShell>
  );
}
