import { useEffect, useMemo, useState } from "react";
import { fetchMemories, type MemorySchema } from "../api/memories";

type Props = {
  enabled: boolean;
};

const MEMORY_TYPE_ORDER = [
  "stable_profile",
  "job_progress",
  "reminder",
  "project",
  "recent_event",
  "behavior_preference",
  "relationship_state",
  "conversation_summary",
] as const;

const MEMORY_TYPE_LABELS: Record<string, string> = {
  stable_profile: "画像",
  job_progress: "求职进展",
  reminder: "提醒",
  project: "项目",
  recent_event: "近况",
  behavior_preference: "偏好",
  relationship_state: "印象",
  conversation_summary: "摘要",
};

const WRITER_LABELS: Record<string, string> = {
  llm: "llm",
  rule_based: "规则",
  reflection: "反思",
};

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function isMemoryExpired(expiresAt: string | null): boolean {
  if (!expiresAt) {
    return false;
  }

  const expiresMs = Date.parse(expiresAt);
  if (Number.isNaN(expiresMs)) {
    return false;
  }

  return expiresMs <= Date.now();
}

function getWriterLabel(metadata: Record<string, unknown>): string | null {
  const writer = metadata.writer;
  if (typeof writer !== "string") {
    return null;
  }

  return WRITER_LABELS[writer] ?? null;
}

function groupMemories(memories: MemorySchema[]): Array<{ type: string; label: string; items: MemorySchema[] }> {
  const grouped = new Map<string, MemorySchema[]>();

  for (const memory of memories) {
    const bucket = grouped.get(memory.type) ?? [];
    bucket.push(memory);
    grouped.set(memory.type, bucket);
  }

  const orderedTypes = [
    ...MEMORY_TYPE_ORDER.filter((type) => grouped.has(type)),
    ...[...grouped.keys()].filter((type) => !MEMORY_TYPE_ORDER.includes(type as (typeof MEMORY_TYPE_ORDER)[number])).sort(),
  ];

  return orderedTypes.map((type) => {
    const items = [...(grouped.get(type) ?? [])].sort((left, right) => {
      if (right.importance !== left.importance) {
        return right.importance - left.importance;
      }

      return Date.parse(right.updated_at) - Date.parse(left.updated_at);
    });

    return {
      type,
      label: MEMORY_TYPE_LABELS[type] ?? type,
      items,
    };
  });
}

export function MemoryPanel({ enabled }: Props) {
  const [memories, setMemories] = useState<MemorySchema[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "offline">("loading");

  useEffect(() => {
    if (!enabled) {
      setStatus("offline");
      return;
    }

    let active = true;

    async function load() {
      try {
        const loaded = await fetchMemories(undefined, 50);
        if (!active) {
          return;
        }

        setMemories(loaded.filter((memory) => !isMemoryExpired(memory.expires_at)));
        setStatus("ready");
      } catch {
        if (!active) {
          return;
        }

        setStatus("offline");
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [enabled]);

  const groups = useMemo(() => groupMemories(memories), [memories]);

  return (
    <details className="memory-panel">
      <summary>Boxi 的记忆</summary>
      {status === "loading" ? <p className="memory-copy">加载记忆…</p> : null}
      {status === "offline" ? <p className="memory-copy">记忆面板需要本地 API。</p> : null}
      {status === "ready" && groups.length === 0 ? (
        <p className="memory-copy">Boxi 还没记住什么。</p>
      ) : null}
      {status === "ready" && groups.length > 0 ? (
        <div className="memory-groups">
          {groups.map((group) => (
            <section key={group.type} className="memory-group">
              <h3 className="memory-group-title">{group.label}</h3>
              <ul className="memory-list">
                {group.items.map((memory) => {
                  const writerLabel = getWriterLabel(memory.metadata);

                  return (
                    <li key={memory.id} className="memory-item">
                      <p className="memory-content">{memory.content}</p>
                      <div className="memory-meta">
                        <span className="memory-importance">{formatPercent(memory.importance)}</span>
                        {writerLabel ? (
                          <span className="memory-writer-badge">{writerLabel}</span>
                        ) : null}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
      ) : null}
    </details>
  );
}
