export const MEMORY_TYPE_LABELS: Record<string, string> = {
  stable_profile: "画像",
  job_progress: "求职进展",
  reminder: "提醒",
  project: "项目",
  recent_event: "近况",
  behavior_preference: "偏好",
  relationship_state: "印象",
  conversation_summary: "摘要",
};

export function formatMemoryTypeLabel(type: string): string {
  return MEMORY_TYPE_LABELS[type] ?? type;
}
