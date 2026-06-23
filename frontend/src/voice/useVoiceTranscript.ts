import { useEffect, useRef, useState } from "react";

export type TranscriptRole = "user" | "boxi";

export type TranscriptEntry = {
  role: TranscriptRole;
  text: string;
  ts: number;
};

const MAX_ENTRIES = 20;

function toWebSocketUrl(apiBaseUrl: string): string {
  return `${apiBaseUrl.replace(/^http/, "ws")}/realtime/transcript`;
}

/** Subscribes to the Pipecat transcript WebSocket while `enabled`; closes otherwise. */
export function useVoiceTranscript(enabled: boolean, apiBaseUrl: string): TranscriptEntry[] {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled) {
      setEntries([]);
      return;
    }

    const socket = new WebSocket(toWebSocketUrl(apiBaseUrl));
    socketRef.current = socket;

    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const data = JSON.parse(event.data) as TranscriptEntry;
        setEntries((prev) => [...prev, data].slice(-MAX_ENTRIES));
      } catch {
        // malformed event — ignore, transcript is best-effort debug UI
      }
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [enabled, apiBaseUrl]);

  return entries;
}
