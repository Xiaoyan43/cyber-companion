const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type MemoryWriter = "llm" | "rule_based" | "reflection";

export type MemorySchema = {
  id: number;
  created_at: string;
  updated_at: string;
  type: string;
  content: string;
  tags: string[];
  importance: number;
  confidence: number;
  expires_at: string | null;
  source_message_id: number | null;
  metadata: Record<string, unknown>;
};

export type MemoryListResponse = {
  memories: MemorySchema[];
};

export async function fetchMemories(
  type?: string,
  limit = 50,
): Promise<MemorySchema[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (type) {
    params.set("type", type);
  }

  const response = await fetch(`${apiBaseUrl}/memory/memories?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to load memories with HTTP ${response.status}`);
  }

  const payload = (await response.json()) as MemoryListResponse;
  return payload.memories;
}
