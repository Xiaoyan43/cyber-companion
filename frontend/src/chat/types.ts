import type { ChatCompleteResponse, ChatStreamDoneMeta } from "../api/chat";
import type { StoredMessage } from "../api/messages";

export type MessageMeta = {
  provider?: string;
  model?: string;
  mock?: boolean;
  decision?: string;
  shouldCallLlm?: boolean;
  usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  cost?: {
    input_usd: number;
    output_usd: number;
    total_usd: number;
    pricing_source: string;
  };
};

export type ChatMessage = {
  id: number;
  speaker: "boxi" | "user";
  text: string;
  meta?: MessageMeta;
  /** Marks a proactive initiation bubble (PI-3 delivery). */
  initiation?: "proactive";
  /** Bilingual reply translation (P11), only present on the turn it was generated for. */
  translation?: string | null;
};

export type TurnSummary = {
  provider: string;
  model: string;
  mock: boolean;
  decision: string;
  shouldCallLlm: boolean;
  usage: ChatCompleteResponse["usage"];
  cost: ChatCompleteResponse["cost"];
};

function readMessageMeta(metadata: Record<string, unknown>): MessageMeta | undefined {
  if (!metadata || Object.keys(metadata).length === 0) {
    return undefined;
  }

  const usage = metadata.usage;
  const cost = metadata.cost;

  return {
    provider: typeof metadata.provider === "string" ? metadata.provider : undefined,
    model: typeof metadata.model === "string" ? metadata.model : undefined,
    mock: typeof metadata.mock === "boolean" ? metadata.mock : undefined,
    decision: typeof metadata.decision === "string" ? metadata.decision : undefined,
    shouldCallLlm:
      typeof metadata.should_call_llm === "boolean" ? metadata.should_call_llm : undefined,
    usage:
      usage &&
      typeof usage === "object" &&
      typeof (usage as { input_tokens?: unknown }).input_tokens === "number"
        ? (usage as MessageMeta["usage"])
        : undefined,
    cost:
      cost &&
      typeof cost === "object" &&
      typeof (cost as { total_usd?: unknown }).total_usd === "number"
        ? (cost as MessageMeta["cost"])
        : undefined,
  };
}

export function storedMessageToChatMessage(message: StoredMessage): ChatMessage | null {
  const text = message.content.trim();
  if (message.role === "user" && !text) {
    return null;
  }

  return {
    id: message.id,
    speaker: message.role === "assistant" ? "boxi" : "user",
    text: message.content,
    meta: message.role === "assistant" ? readMessageMeta(message.metadata) : undefined,
    initiation:
      message.role === "assistant" && message.metadata?.decision === "proactive"
        ? "proactive"
        : undefined,
    translation:
      message.role === "assistant" && typeof message.metadata?.translation === "string"
        ? message.metadata.translation
        : undefined,
  };
}

export function streamMetaToTurnSummary(meta: ChatStreamDoneMeta): TurnSummary {
  return {
    provider: meta.provider,
    model: meta.model,
    mock: meta.provider === "mock",
    decision: meta.decision,
    shouldCallLlm: meta.should_call_llm,
    usage: meta.usage,
    cost: meta.cost,
  };
}

export function streamMetaToMessageMeta(meta: ChatStreamDoneMeta): MessageMeta {
  return {
    provider: meta.provider,
    model: meta.model,
    mock: meta.provider === "mock",
    decision: meta.decision,
    shouldCallLlm: meta.should_call_llm,
    usage: meta.usage,
    cost: meta.cost,
  };
}

export function completionToTurnSummary(completion: ChatCompleteResponse): TurnSummary {
  return {
    provider: completion.provider,
    model: completion.model,
    mock: completion.mock,
    decision: completion.decision,
    shouldCallLlm: completion.should_call_llm,
    usage: completion.usage,
    cost: completion.cost,
  };
}

export function messageMetaToTurnSummary(meta: MessageMeta): TurnSummary | null {
  if (!meta.usage || !meta.cost) {
    return null;
  }

  const provider = meta.provider ?? "local";
  const shouldCallLlm =
    typeof meta.shouldCallLlm === "boolean"
      ? meta.shouldCallLlm
      : provider !== "local-behavior";

  return {
    provider,
    model: meta.model ?? "unknown",
    mock: meta.mock ?? false,
    decision: meta.decision ?? "reply",
    shouldCallLlm,
    usage: meta.usage,
    cost: meta.cost,
  };
}

export function restoreLastTurnFromMessages(messages: ChatMessage[]): TurnSummary | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.speaker !== "boxi" || !message.meta) {
      continue;
    }

    const summary = messageMetaToTurnSummary(message.meta);
    if (summary) {
      return summary;
    }
  }

  return null;
}

export function formatUsd(value: number): string {
  if (value === 0) {
    return "$0.0000";
  }

  if (value < 0.01) {
    return `$${value.toFixed(4)}`;
  }

  return `$${value.toFixed(3)}`;
}

export function formatMessageMeta(meta: MessageMeta): string | null {
  if (!meta.usage && !meta.cost) {
    return null;
  }

  const tokens = meta.usage ? `${meta.usage.total_tokens} tok` : null;
  const cost = meta.cost ? formatUsd(meta.cost.total_usd) : null;
  const provider = meta.provider ?? "local";

  return [provider, tokens, cost].filter(Boolean).join(" · ");
}
