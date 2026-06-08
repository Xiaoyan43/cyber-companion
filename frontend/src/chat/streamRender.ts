import type { ChatMessage } from "./types";

export function appendChatStreamDelta(
  messages: ChatMessage[],
  messageId: number,
  delta: string,
): ChatMessage[] {
  return messages.map((message) =>
    message.id === messageId ? { ...message, text: message.text + delta } : message,
  );
}
