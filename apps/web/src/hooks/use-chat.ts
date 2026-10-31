import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chatService } from "../services/chat-service";
import { ChatKeys } from "./query-keys";
import { messageSyncOptions } from "../services/message-sync";

export function useConversations(enabled = true) {
  return useQuery({
    queryKey: ChatKeys.conversations(),
    queryFn: () => chatService.listConversations(),
    enabled,
    ...messageSyncOptions,
  });
}

export function useMessages(conversationId: string | null, paused = false) {
  return useQuery({
    queryKey: ChatKeys.messages(conversationId ?? ""),
    queryFn: ({ signal }) => chatService.listMessages(conversationId!, signal),
    enabled: Boolean(conversationId) && !paused,
    ...messageSyncOptions,
  });
}

export function useCreateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title?: string) => chatService.createConversation(title),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ChatKeys.conversations() });
    },
  });
}

export function useSendMessage(conversationId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => {
      if (!conversationId) throw new Error("无活跃会话");
      return chatService.sendMessage(conversationId, content);
    },
    onSuccess: () => {
      if (!conversationId) return;
      void qc.invalidateQueries({
        queryKey: ChatKeys.messages(conversationId),
      });
      void qc.invalidateQueries({ queryKey: ChatKeys.conversations() });
    },
  });
}
