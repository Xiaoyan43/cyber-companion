const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type MemoryLink = {
  id: number;
  memory_id: number;
  related_memory_id: number;
  relation: string;
  created_at: string;
  memory_type: string;
  memory_content: string;
  related_type: string;
  related_content: string;
};

export type MemoryLinkListResponse = {
  links: MemoryLink[];
};

export async function fetchMemoryLinks(limit = 100): Promise<MemoryLink[]> {
  const response = await fetch(`${apiBaseUrl}/memory/links?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to load memory links with HTTP ${response.status}`);
  }

  const payload = (await response.json()) as MemoryLinkListResponse;
  return payload.links;
}
