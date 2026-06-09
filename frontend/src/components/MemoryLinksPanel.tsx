import { useEffect, useState } from "react";
import { fetchMemoryLinks, type MemoryLink } from "../api/memoryLinks";
import { formatMemoryTypeLabel } from "../memory/typeLabels";

type Props = {
  enabled: boolean;
};

function formatLinkEndpoint(type: string, content: string): string {
  return `(${formatMemoryTypeLabel(type)}) ${content}`;
}

export function MemoryLinksPanel({ enabled }: Props) {
  const [links, setLinks] = useState<MemoryLink[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "offline">("loading");

  useEffect(() => {
    if (!enabled) {
      setStatus("offline");
      return;
    }

    let active = true;

    async function load() {
      try {
        const loaded = await fetchMemoryLinks();
        if (!active) {
          return;
        }

        setLinks(loaded);
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
    <details className="memory-links-panel">
      <summary>Boxi 把这些联系起来了</summary>
      {status === "loading" ? <p className="memory-copy">加载记忆连边…</p> : null}
      {status === "offline" ? <p className="memory-copy">联系面板需要本地 API。</p> : null}
      {status === "ready" && links.length === 0 ? (
        <p className="memory-copy">Boxi 还没把任何事联系起来。</p>
      ) : null}
      {status === "ready" && links.length > 0 ? (
        <ul className="memory-links-list">
          {links.map((link) => (
            <li key={link.id} className="memory-link-row">
              <span>{formatLinkEndpoint(link.memory_type, link.memory_content)}</span>
              <span className="memory-link-arrow" aria-hidden="true">
                ↔
              </span>
              <span>{formatLinkEndpoint(link.related_type, link.related_content)}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </details>
  );
}
