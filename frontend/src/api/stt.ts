const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type STTStatusResponse = {
  enabled: boolean;
  default_provider: string;
  force_mock: boolean;
  allow_cloud_stt: boolean;
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

export type STTTranscribeResponse = {
  provider: string;
  model: string;
  text: string;
  mock: boolean;
  language?: string | null;
};

export async function fetchSttStatus(): Promise<STTStatusResponse> {
  const response = await fetch(`${apiBaseUrl}/stt/status`);

  if (!response.ok) {
    throw new Error(`Failed to load STT status with HTTP ${response.status}`);
  }

  return (await response.json()) as STTStatusResponse;
}

export async function transcribeAudio(
  blob: Blob,
  filename = "recording.webm",
): Promise<STTTranscribeResponse> {
  const formData = new FormData();
  formData.append("audio", blob, filename);

  const response = await fetch(`${apiBaseUrl}/stt/transcribe`, {
    method: "POST",
    body: formData,
  });

  const payload = (await response.json()) as
    | STTTranscribeResponse
    | { detail: { error?: string } };

  if (!response.ok) {
    const detail = "detail" in payload ? payload.detail : undefined;
    const message =
      detail && typeof detail === "object" && "error" in detail
        ? detail.error
        : `STT request failed with HTTP ${response.status}`;
    throw new Error(message ?? "STT request failed");
  }

  return payload as STTTranscribeResponse;
}
