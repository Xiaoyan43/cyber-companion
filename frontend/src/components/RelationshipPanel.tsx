import { useEffect, useState } from "react";
import {
  fetchRelationshipImpression,
  fetchRelationshipState,
  type RelationshipStateResponse,
} from "../api/relationship";

type Props = {
  enabled: boolean;
};

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function RelationshipPanel({ enabled }: Props) {
  const [relationship, setRelationship] = useState<RelationshipStateResponse | null>(null);
  const [impression, setImpression] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "offline">("loading");

  useEffect(() => {
    if (!enabled) {
      setStatus("offline");
      return;
    }

    let active = true;

    async function load() {
      try {
        const [rel, memory] = await Promise.all([
          fetchRelationshipState(),
          fetchRelationshipImpression(),
        ]);
        if (!active) {
          return;
        }
        setRelationship(rel);
        setImpression(memory?.content ?? null);
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
    <details className="relationship-panel">
      <summary>Boxi 怎么看你</summary>
      {status === "loading" ? <p className="relationship-copy">加载关系状态…</p> : null}
      {status === "offline" ? (
        <p className="relationship-copy">关系面板需要本地 API。</p>
      ) : null}
      {status === "ready" && relationship ? (
        <div className="relationship-grid">
          <div>
            <span>信任</span>
            <strong>{formatPercent(relationship.trust)}</strong>
          </div>
          <div>
            <span>亲近</span>
            <strong>{formatPercent(relationship.closeness)}</strong>
          </div>
          <div>
            <span>熟悉</span>
            <strong>{formatPercent(relationship.familiarity)}</strong>
          </div>
          <div>
            <span>张力</span>
            <strong>{formatPercent(relationship.tension)}</strong>
          </div>
          {impression ? (
            <p className="relationship-impression">{impression}</p>
          ) : (
            <p className="relationship-copy">印象叙事还没形成（SD-4 后台层会写入）。</p>
          )}
        </div>
      ) : null}
    </details>
  );
}
