const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type MoodStateResponse = {
  updated_at: string;
  mood: string;
  energy: number;
  annoyance: number;
  boredom: number;
  worry: number;
  trust: number;
  loneliness: number;
  metadata: Record<string, unknown>;
};

export async function fetchMoodState(): Promise<MoodStateResponse> {
  const response = await fetch(`${apiBaseUrl}/memory/mood`);

  if (!response.ok) {
    throw new Error(`Failed to load mood with HTTP ${response.status}`);
  }

  return (await response.json()) as MoodStateResponse;
}
