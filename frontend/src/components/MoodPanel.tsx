import { useEffect, useState } from "react";
import { fetchMoodState, type MoodStateResponse } from "../api/mood";

type Props = {
  enabled: boolean;
};

const MOOD_LABELS: Record<string, string> = {
  idle: "发呆",
  happy: "来劲",
  sad: "低落",
  angry: "生气",
  sleepy: "犯困",
  thinking: "琢磨",
  talking: "话多",
  worried: "担心",
  annoyed: "不爽",
  silent: "沉默",
};

const MOOD_STATS = [
  { key: "energy", label: "精力" },
  { key: "annoyance", label: "烦躁" },
  { key: "boredom", label: "无聊" },
  { key: "worry", label: "担心" },
  { key: "loneliness", label: "孤独" },
] as const;

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatMoodLabel(mood: string): string {
  return MOOD_LABELS[mood] ?? mood;
}

export function MoodPanel({ enabled }: Props) {
  const [moodState, setMoodState] = useState<MoodStateResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "offline">("loading");

  useEffect(() => {
    if (!enabled) {
      setStatus("offline");
      return;
    }

    let active = true;

    async function load() {
      try {
        const state = await fetchMoodState();
        if (!active) {
          return;
        }

        setMoodState(state);
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

  return (
    <details className="mood-panel">
      <summary>Boxi 此刻心情</summary>
      {status === "loading" ? <p className="mood-copy">加载心情状态…</p> : null}
      {status === "offline" ? <p className="mood-copy">心情面板需要本地 API。</p> : null}
      {status === "ready" && moodState ? (
        <div className="mood-body">
          <p className="mood-label">{formatMoodLabel(moodState.mood)}</p>
          <div className="mood-stats">
            {MOOD_STATS.map((stat) => {
              const value = moodState[stat.key];
              const percent = formatPercent(value);

              return (
                <div key={stat.key} className="mood-stat">
                  <div className="mood-stat-header">
                    <span>{stat.label}</span>
                    <strong>{percent}</strong>
                  </div>
                  <div
                    className="mood-stat-bar"
                    role="progressbar"
                    aria-valuenow={Math.round(value * 100)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={stat.label}
                  >
                    <div className="mood-stat-fill" style={{ width: percent }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </details>
  );
}
