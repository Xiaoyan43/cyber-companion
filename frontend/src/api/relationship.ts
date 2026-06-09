const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type RelationshipStateResponse = {
  updated_at: string;
  trust: number;
  closeness: number;
  familiarity: number;
  tension: number;
  last_meaningful_interaction_at: string | null;
  metadata: Record<string, unknown>;
};

export type RelationshipMemory = {
  id: number;
  content: string;
  updated_at: string;
};

export async function fetchRelationshipState(): Promise<RelationshipStateResponse> {
  const response = await fetch(`${apiBaseUrl}/memory/relationship`);
  if (!response.ok) {
    throw new Error(`Failed to load relationship with HTTP ${response.status}`);
  }
  return (await response.json()) as RelationshipStateResponse;
}

export async function fetchRelationshipImpression(): Promise<RelationshipMemory | null> {
  const response = await fetch(`${apiBaseUrl}/memory/memories?type=relationship_state&limit=1`);
  if (!response.ok) {
    throw new Error(`Failed to load impression memory with HTTP ${response.status}`);
  }
  const payload = (await response.json()) as { memories: RelationshipMemory[] };
  return payload.memories[0] ?? null;
}
