const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type ChatUsage = {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
};

export type ChatCost = {
  input_usd: number;
  output_usd: number;
  total_usd: number;
  pricing_source: string;
};

export type ChatCompleteResponse = {
  provider: string;
  model: string;
  content: string;
  usage: ChatUsage;
  cost: ChatCost;
  mock: boolean;
  avatar_state: string;
  decision: string;
  should_call_llm: boolean;
};

export type ChatCompleteError = {
  error: string;
  provider?: string;
};

export type ChatStreamDoneMeta = {
  provider: string;
  model: string;
  decision: string;
  avatar_state: string;
  should_call_llm: boolean;
  usage: ChatUsage;
  cost: ChatCost;
};

export type ChatStreamResult = {
  content: string;
  meta: ChatStreamDoneMeta;
};

export type ChatStreamHandlers = {
  onDelta: (text: string) => void;
  onDone: (meta: ChatStreamDoneMeta) => void;
  onError: (message: string) => void;
};

export class ChatStreamUnsupportedError extends Error {
  constructor(message = "Streaming not supported") {
    super(message);
    this.name = "ChatStreamUnsupportedError";
  }
}

export function parseSseDataLine(line: string): Record<string, unknown> | null {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith(":")) {
    return null;
  }

  if (!trimmed.startsWith("data:")) {
    return null;
  }

  const payload = trimmed.slice("data:".length).trim();
  if (!payload) {
    return null;
  }

  return JSON.parse(payload) as Record<string, unknown>;
}

export function processSseLines(
  chunk: string,
  onEvent: (event: Record<string, unknown>) => void,
): string {
  const lines = chunk.split("\n");
  const remainder = lines.pop() ?? "";

  for (const line of lines) {
    const event = parseSseDataLine(line);
    if (event) {
      onEvent(event);
    }
  }

  return remainder;
}

function isChatStreamDoneMeta(value: unknown): value is ChatStreamDoneMeta {
  if (!value || typeof value !== "object") {
    return false;
  }

  const meta = value as ChatStreamDoneMeta;
  return (
    typeof meta.provider === "string" &&
    typeof meta.model === "string" &&
    typeof meta.decision === "string" &&
    typeof meta.avatar_state === "string" &&
    typeof meta.should_call_llm === "boolean" &&
    typeof meta.usage === "object" &&
    meta.usage !== null &&
    typeof meta.cost === "object" &&
    meta.cost !== null
  );
}

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

export async function requestChatStream(
  userText: string,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<ChatStreamResult> {
  const response = await fetch(`${apiBaseUrl}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      messages: [{ role: "user", content: userText }],
    }),
    signal,
  });

  if (response.status === 404 || response.status === 405) {
    throw new ChatStreamUnsupportedError(`HTTP ${response.status}`);
  }

  if (!response.ok) {
    let message = `Chat stream failed with HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: ChatCompleteError };
      if (payload.detail?.error) {
        message = payload.detail.error;
      }
    } catch {
      // Keep the HTTP status message when the body is not JSON.
    }
    throw new Error(message);
  }

  if (!response.body) {
    throw new ChatStreamUnsupportedError("Response body is not readable");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let accumulated = "";
  let doneMeta: ChatStreamDoneMeta | null = null;

  const handleEvent = (event: Record<string, unknown>) => {
    if (event.type === "delta" && typeof event.text === "string") {
      accumulated += event.text;
      handlers.onDelta(event.text);
      return;
    }

    if (event.type === "done") {
      if (!isChatStreamDoneMeta(event.meta)) {
        throw new Error("Stream done event missing meta");
      }
      doneMeta = event.meta;
      handlers.onDone(event.meta);
      return;
    }

    if (event.type === "error") {
      const message = typeof event.message === "string" ? event.message : "Stream error";
      handlers.onError(message);
      throw new Error(message);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    buffer = processSseLines(buffer, handleEvent);
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    buffer = processSseLines(`${buffer}\n`, handleEvent);
  }

  if (!doneMeta) {
    throw new Error("Stream ended without done event");
  }

  return { content: accumulated, meta: doneMeta };
}
