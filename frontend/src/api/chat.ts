const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type ChatCompleteResponse = {
  provider: string;
  model: string;
  content: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  cost: {
    input_usd: number;
    output_usd: number;
    total_usd: number;
    pricing_source: string;
  };
  mock: boolean;
  avatar_state: string;
  decision: string;
  should_call_llm: boolean;
};

export type ChatCompleteError = {
  error: string;
  provider?: string;
};

export async function requestChatComplete(userText: string): Promise<ChatCompleteResponse> {
  const response = await fetch(`${apiBaseUrl}/chat/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      messages: [{ role: "user", content: userText }],
    }),
  });

  const payload = (await response.json()) as ChatCompleteResponse | { detail: ChatCompleteError };

  if (!response.ok) {
    const detail = "detail" in payload ? payload.detail : undefined;
    const message =
      detail && typeof detail === "object" && "error" in detail
        ? detail.error
        : `Chat request failed with HTTP ${response.status}`;
    throw new Error(message);
  }

  return payload as ChatCompleteResponse;
}
