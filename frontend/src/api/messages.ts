const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type StoredMessage = {
  id: number;
  created_at: string;
  role: string;
  content: string;
  source: string;
  metadata: Record<string, unknown>;
};

export type MessageListResponse = {
  messages: StoredMessage[];
};

export async function fetchStoredMessages(limit = 50): Promise<StoredMessage[]> {
  const response = await fetch(`${apiBaseUrl}/memory/messages?limit=${limit}`);

  if (!response.ok) {
    throw new Error(`Failed to load messages with HTTP ${response.status}`);
  }

  const payload = (await response.json()) as MessageListResponse;
  return payload.messages;
}
