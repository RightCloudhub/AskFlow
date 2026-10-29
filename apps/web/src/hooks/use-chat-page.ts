import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { setToken } from "../api/client";
import { useMe } from "./use-auth";
import { useConversations, useCreateConversation, useMessages } from "./use-chat";
import { useChatTransport } from "./use-chat-transport";

const TITLE_LENGTH = 20;

export function useChatPage() {
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [handoffHint, setHandoffHint] = useState<string | null>(null);
  const appliedLink = useRef("");
  const meQ = useMe();
  const convQ = useConversations(meQ.isSuccess);
  const msgQ = useMessages(activeId);
  const createConv = useCreateConversation();
  const transport = useChatTransport(setHandoffHint);
  const requested = params.get("conversation_id") ?? "";
  useEffect(() => {
    if (meQ.isError) { setToken(null); nav("/login"); }
  }, [meQ.isError, nav]);
  useEffect(() => {
    if (requested && requested !== appliedLink.current && convQ.data?.some((row) => row.id === requested)) {
      setActiveId(requested);
      appliedLink.current = requested;
    } else if (!activeId && convQ.data?.[0]) setActiveId(convQ.data[0].id);
  }, [requested, activeId, convQ.data]);
  function select(id: string) {
    setActiveId(id);
    setHandoffHint(null);
    setParams({}, { replace: true });
  }
  async function create() { select((await createConv.mutateAsync("新会话")).id); }
  async function suggest(content: string) {
    if (transport.streaming) return;
    const id = activeId ?? (await createConv.mutateAsync(content.slice(0, TITLE_LENGTH))).id;
    setActiveId(id);
    await transport.send(content, id);
  }
  const active = convQ.data?.find((row) => row.id === activeId);
  return { nav, meQ, convQ, msgQ, activeId, active, handoffHint, ...transport, select, create, suggest,
    creating: createConv.isPending, loading: meQ.isLoading || (meQ.isSuccess && convQ.isLoading) };
}
