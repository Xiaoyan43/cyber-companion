import { useEffect, useRef } from "react";
import type { TranscriptEntry } from "../voice/useVoiceTranscript";
import type { PipecatVoicePhase } from "../voice/usePipecatVoice";

type PipecatVoicePanelProps = {
  phase: PipecatVoicePhase;
  error: string | null;
  transcript: TranscriptEntry[];
  onStart: () => void;
  onStop: () => void;
  disabled?: boolean;
};

const phaseLabels: Record<PipecatVoicePhase, string> = {
  checking: "检查中…",
  stopped: "未连接",
  starting: "启动中…",
  running: "通话中",
  stopping: "停止中…",
  error: "启动失败",
};

export function PipecatVoicePanel({
  phase,
  error,
  transcript,
  onStart,
  onStop,
  disabled = false,
}: PipecatVoicePanelProps) {
  const transcriptRef = useRef<HTMLDivElement>(null);
  const isRunning = phase === "running";
  const isBusy = phase === "checking" || phase === "starting" || phase === "stopping";

  useEffect(() => {
    const container = transcriptRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [transcript.length, transcript[transcript.length - 1]?.ts]);

  return (
    <section className={`soul-voice-panel${isRunning ? " live" : ""}`} aria-label="Soul voice">
      <div className="rtc-voice-header">
        <span className="rtc-voice-title">Soul 语音</span>
        <span className="rtc-voice-phase" aria-live="polite">{phaseLabels[phase]}</span>
      </div>

      <div className="rtc-voice-meta">
        <span className="soul-voice-badge">Shared Soul</span>
        <span className="soul-voice-transport" title="声音由本机后端进程连接麦克风与扬声器">
          本机麦克风 + 扬声器
        </span>
      </div>

      {isRunning ? (
        <div className="rtc-subtitle-list" ref={transcriptRef} aria-live="polite">
          {transcript.length === 0 ? (
            <p className="rtc-subtitle-empty">我在听。说点什么。</p>
          ) : (
            transcript.map((entry) => (
              <div key={`${entry.ts}-${entry.role}`} className={`rtc-subtitle-line ${entry.role}`}>
                <span className="rtc-subtitle-speaker">{entry.role === "boxi" ? "Boxi" : "你"}</span>
                <p>{entry.text}</p>
              </div>
            ))
          )}
        </div>
      ) : (
        <p className="soul-voice-description">
          默认语音入口。每轮回复先经过 Boxi 的行为、记忆与人格内核，再交给语音合成。
        </p>
      )}

      <div className="rtc-voice-actions">
        {isRunning ? (
          <button type="button" className="rtc-leave-button" disabled={disabled} onClick={onStop}>
            结束 Soul 语音
          </button>
        ) : (
          <button
            type="button"
            className="rtc-join-button"
            disabled={disabled || isBusy}
            onClick={onStart}
          >
            {phase === "starting" ? "正在启动…" : "开始 Soul 语音"}
          </button>
        )}
      </div>

      {error ? <p className="rtc-voice-error">{error}</p> : null}
    </section>
  );
}
