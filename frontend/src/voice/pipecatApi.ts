const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type PipecatBackendStatus = {
  status: "running" | "stopped";
  last_error: string | null;
};

type PipecatCommandResponse = {
  status: "started" | "already_running" | "stopped" | "not_running";
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);
  if (!response.ok) {
    throw new Error(`Soul voice request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function fetchPipecatStatus(): Promise<PipecatBackendStatus> {
  return requestJson<PipecatBackendStatus>("/realtime/status");
}

export function startPipecat(): Promise<PipecatCommandResponse> {
  return requestJson<PipecatCommandResponse>("/realtime/start", { method: "POST" });
}

export function stopPipecat(): Promise<PipecatCommandResponse> {
  return requestJson<PipecatCommandResponse>("/realtime/stop", { method: "POST" });
}
