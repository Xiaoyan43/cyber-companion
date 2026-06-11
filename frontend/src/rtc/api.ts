import { formatRtcApiError } from "./apiErrors";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type RtcMode = "pure" | "hybrid";

export type RtcStatus = {
  base_configured: boolean;
  pure_ready: boolean;
  hybrid_ready: boolean;
  missing_pure: string[];
  missing_hybrid: string[];
  viking_memory_enabled?: boolean;
  viking_memory_write_ready?: boolean;
  sqlite_memory_ready?: boolean;
  default_user_id?: string;
};

export type RtcMemorySubtitle = {
  speaker: "user" | "boxi";
  text: string;
};

export type RtcPrepareResponse = {
  mode: RtcMode;
  output_mode: number;
  app_id: string;
  room_id: string;
  user_id: string;
  token: string;
  bot_user_id: string;
  task_id: string;
  welcome_message: string;
};

export async function fetchRtcStatus(): Promise<RtcStatus> {
  const response = await fetch(`${apiBaseUrl}/rtc/status`);
  if (!response.ok) {
    throw new Error(`RTC status failed (${response.status})`);
  }
  return response.json() as Promise<RtcStatus>;
}

export async function prepareRtcSession(mode: RtcMode): Promise<RtcPrepareResponse> {
  const response = await fetch(`${apiBaseUrl}/rtc/prepare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(formatRtcApiError(detail, `RTC prepare failed (${response.status})`));
  }
  return response.json() as Promise<RtcPrepareResponse>;
}

export type RtcStancePreview = {
  default_welcome: string;
  welcome_message: string;
  state_block: string;
  steering_directive: string;
};

export async function fetchRtcStancePreview(): Promise<RtcStancePreview> {
  const response = await fetch(`${apiBaseUrl}/rtc/stance-preview`);
  if (!response.ok) {
    throw new Error(`RTC stance preview failed (${response.status})`);
  }
  return response.json() as Promise<RtcStancePreview>;
}

export async function startRtcAgent(
  mode: RtcMode,
  roomId: string,
  userId: string,
): Promise<{ welcome_message: string }> {
  const response = await fetch(`${apiBaseUrl}/rtc/agent/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, room_id: roomId, user_id: userId }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(formatRtcApiError(detail, `RTC agent start failed (${response.status})`));
  }
  return response.json() as Promise<{ status: string; welcome_message: string }>;
}

export async function saveRtcMemorySession(payload: {
  room_id: string;
  user_id: string;
  bot_user_id: string;
  subtitles: RtcMemorySubtitle[];
}): Promise<{ saved: boolean; session_id: string; message_count: number }> {
  const response = await fetch(`${apiBaseUrl}/rtc/memory/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(formatRtcApiError(detail, `RTC memory save failed (${response.status})`));
  }
  return response.json() as Promise<{ saved: boolean; session_id: string; message_count: number }>;
}

/** Fire-and-forget: off-path soul write for one completed voice turn. Never throws. */
export function postRtcTurn(payload: {
  room_id: string;
  user_id: string;
  user_text: string;
  bot_text: string;
}): void {
  void fetch(`${apiBaseUrl}/rtc/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).catch(() => {
    // Must not disturb the live call.
  });
}

export async function stopRtcSession(mode: RtcMode, roomId: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/rtc/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, room_id: roomId }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `RTC stop failed (${response.status})`);
  }
}
