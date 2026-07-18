import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chatService } from "../services/chat-service";
import { ChatKeys } from "./query-keys";

export function useConversations(enabled = true) {
  return useQuery({
    queryKey: ChatKeys.conversations(),
    queryFn: () => chatService.listConversations(),
    enabled,
  });
}

export function useMessages(conversationId: string | null) {
  return useQuery({
    queryKey: ChatKeys.messages(conversationId ?? ""),
    queryFn: () => chatService.listMessages(conversationId!),
    enabled: Boolean(conversationId),
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
