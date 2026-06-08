const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type TTSStatusResponse = {
  enabled: boolean;
  default_provider: string;
  force_mock: boolean;
  allow_cloud_tts: boolean;
  max_speech_chars: number;
  speak_decisions: string[];
  providers: Array<{
    name: string;
    enabled: boolean;
    model: string;
    configured: boolean;
    api_key_present: boolean;
    placeholder: boolean;
    cloud: boolean;
  }>;
};

export type TTSSynthesizeResponse = {
  spoken: boolean;
  reason: string;
  provider?: string | null;
  model?: string | null;
  mime_type?: string | null;
  audio_base64?: string | null;
  duration_ms?: number | null;
  mock?: boolean;
};

export function getTtsApiBaseUrl(): string {
  return apiBaseUrl;
}

export function buildTtsStreamUrl(payload: {
  text: string;
  decision?: string;
  avatarState?: string;
  force?: boolean;
}): string {
  const params = new URLSearchParams();
  params.set("text", payload.text);
  if (payload.decision) {
    params.set("decision", payload.decision);
  }
  if (payload.avatarState) {
    params.set("avatar_state", payload.avatarState);
  }
  if (payload.force) {
    params.set("force", "true");
  }
  return `${apiBaseUrl}/tts/stream?${params.toString()}`;
}

export type TtsStreamProbeResult = "ok" | "skip" | "error";

export async function probeTtsStream(
  url: string,
  signal?: AbortSignal,
): Promise<TtsStreamProbeResult> {
  const response = await fetch(url, { method: "GET", signal });
  if (response.status === 204) {
    return "skip";
  }
  if (!response.ok) {
    return "error";
  }
  await response.body?.cancel();
  return "ok";
}

export async function fetchTtsStatus(): Promise<TTSStatusResponse> {
  const response = await fetch(`${apiBaseUrl}/tts/status`);

  if (!response.ok) {
    throw new Error(`Failed to load TTS status with HTTP ${response.status}`);
  }

  return (await response.json()) as TTSStatusResponse;
}

export async function synthesizeSpeech(payload: {
  text: string;
  decision?: string;
  avatarState?: string;
  force?: boolean;
}): Promise<TTSSynthesizeResponse> {
  const response = await fetch(`${apiBaseUrl}/tts/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: payload.text,
      decision: payload.decision,
      avatar_state: payload.avatarState,
      force: payload.force ?? false,
    }),
  });

  const body = (await response.json()) as
    | TTSSynthesizeResponse
    | { detail: { error?: string } };

  if (!response.ok) {
    const detail = "detail" in body ? body.detail : undefined;
    const message =
      detail && typeof detail === "object" && "error" in detail
        ? detail.error
        : `TTS request failed with HTTP ${response.status}`;
    throw new Error(message ?? "TTS request failed");
  }

  return body as TTSSynthesizeResponse;
}
