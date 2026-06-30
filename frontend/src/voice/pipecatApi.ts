const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type PipecatBackendStatus = {
  status: "running" | "stopped";
  last_error: string | null;
};

type PipecatCommandResponse = {
  status: "started" | "already_running" | "stopped" | "not_running";
};

export type PipecatSdpOffer = {
  sdp: string;
  type: string;
};

export type PipecatSdpAnswer = {
  sdp: string;
  type: string;
  pc_id: string;
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

export function startPipecat(offer: PipecatSdpOffer): Promise<PipecatSdpAnswer> {
  return requestJson<PipecatSdpAnswer>("/realtime/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(offer),
  });
}

export function stopPipecat(): Promise<PipecatCommandResponse> {
  return requestJson<PipecatCommandResponse>("/realtime/stop", { method: "POST" });
}
