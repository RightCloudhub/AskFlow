import { api } from "../api/client";
import type {
  Conversation,
  Message,
  SendMessageResult,
} from "../api/types";

export const chatService = {
  listConversations: () =>
    api<Conversation[]>("/api/v1/chat/conversations"),

  createConversation: (title = "新会话") =>
    api<Conversation>("/api/v1/chat/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),

  listMessages: (conversationId: string) =>
    api<Message[]>(`/api/v1/chat/conversations/${conversationId}/messages`),

  sendMessage: (conversationId: string, content: string) =>
    api<SendMessageResult>(
      `/api/v1/chat/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content }),
      },
    ),
};
