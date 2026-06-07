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
