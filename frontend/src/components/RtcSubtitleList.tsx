import { useEffect, useRef } from "react";
import type { RtcAgentPhase, RtcSubtitleLine } from "../rtc/rtcMessages";

type RtcSubtitleListProps = {
  lines: RtcSubtitleLine[];
  welcomeMessage?: string;
  agentPhase: RtcAgentPhase;
};

export function RtcSubtitleList({ lines, welcomeMessage, agentPhase }: RtcSubtitleListProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [lines.length, lines[lines.length - 1]?.text]);

  const showWaiting = lines.length === 0 && agentPhase !== "speaking";

  return (
    <div className="rtc-subtitle-list" ref={containerRef} aria-live="polite">
      {showWaiting ? (
        <p className="rtc-subtitle-empty">
          {welcomeMessage ? `${welcomeMessage}（说点什么）` : "AI 准备中，请稍候…"}
        </p>
      ) : null}
      {lines.map((line) => (
        <div key={line.id} className={`rtc-subtitle-line ${line.speaker}`}>
          <span className="rtc-subtitle-speaker">{line.speaker === "boxi" ? "Boxi" : "你"}</span>
          <p>{line.text}</p>
          {line.interrupted ? <span className="rtc-interrupt-tag">已打断</span> : null}
        </div>
      ))}
    </div>
  );
}
