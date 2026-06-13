const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type BehaviorDecision = {
  decision: string;
  avatar_state: string;
  should_call_llm: boolean;
  reason: string;
  local_response?: string | null;
  tone_mode: string;
  saved_message_id?: number | null;
};

export type BehaviorEventType = "user_message" | "proactive_check" | "idle_tick";

export async function evaluateBehavior(
  eventType: BehaviorEventType,
  userInput = "",
  options?: { forceProactive?: boolean },
): Promise<BehaviorDecision> {
  const response = await fetch(`${apiBaseUrl}/behavior/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      event_type: eventType,
      user_input: userInput,
      force_proactive: options?.forceProactive === true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Behavior evaluate failed with HTTP ${response.status}`);
  }

  return (await response.json()) as BehaviorDecision;
}
