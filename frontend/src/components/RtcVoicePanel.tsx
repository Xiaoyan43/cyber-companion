import type { RtcMode } from "../rtc/api";
import type { RtcAgentPhase, RtcSubtitleLine } from "../rtc/rtcMessages";
import type { VikingMemorySaveState } from "../rtc/vikingMemoryBadge";
import { RtcSubtitleList } from "./RtcSubtitleList";
import { RtcVikingMemoryBadge } from "./RtcVikingMemoryBadge";

type RtcVoicePanelProps = {
  mode: RtcMode;
  onModeChange: (mode: RtcMode) => void;
  modeReady: boolean;
  pureReady: boolean;
  hybridReady: boolean;
  phaseLabel: string;
  agentPhase: RtcAgentPhase;
  error: string | null;
  isLive: boolean;
  subtitles: RtcSubtitleLine[];
  welcomeMessage?: string;
  autoplayBlocked: boolean;
  micActive: boolean;
  onJoin: () => void;
  onLeave: () => void;
  onResumeAudio: () => void;
  disabled?: boolean;
  vikingMemoryEnabled?: boolean;
  vikingMemoryWriteReady?: boolean;
  vikingUserId?: string;
  vikingMemorySaveState?: VikingMemorySaveState;
  sqliteMemoryReady?: boolean;
};

const agentPhaseLabel: Record<RtcAgentPhase, string> = {
  idle: "待命",
  listening: "在听",
  thinking: "在想",
  speaking: "在说",
};

export function RtcVoicePanel({
  mode,
  onModeChange,
  modeReady,
  pureReady,
  hybridReady,
  phaseLabel,
  agentPhase,
  error,
  isLive,
  subtitles,
  welcomeMessage,
  autoplayBlocked,
  micActive,
  onJoin,
  onLeave,
  onResumeAudio,
  disabled = false,
  vikingMemoryEnabled = false,
  vikingMemoryWriteReady = false,
  vikingUserId,
  vikingMemorySaveState = "idle",
  sqliteMemoryReady = false,
}: RtcVoicePanelProps) {
  return (
    <div className={`rtc-voice-panel${isLive ? " live" : ""}`}>
      <div className="rtc-voice-header">
        <span className="rtc-voice-title">RTC 语音 v2</span>
        <span className="rtc-voice-phase">{phaseLabel}</span>
      </div>

      <div className="rtc-voice-meta">
        <RtcVikingMemoryBadge
          enabled={vikingMemoryEnabled}
          writeReady={vikingMemoryWriteReady}
          userId={vikingUserId}
          saveState={vikingMemorySaveState}
        />
        <span
          className={`rtc-viking-badge tone-${sqliteMemoryReady ? "ready" : "off"}`}
          title={
            sqliteMemoryReady
              ? "进房时会注入右侧文字聊天的近期记录"
              : "暂无右侧文字聊天记录可注入"
          }
        >
          {sqliteMemoryReady ? "文字记忆 就绪" : "文字记忆 空"}
        </span>
      </div>

      {!isLive ? (
        <div className="rtc-mode-toggle" role="radiogroup" aria-label="RTC brain mode">
          <label className={mode === "pure" ? "rtc-mode active" : "rtc-mode"}>
            <input
              type="radio"
              name="rtc-mode"
              value="pure"
              checked={mode === "pure"}
              disabled={disabled}
              onChange={() => onModeChange("pure")}
            />
            纯 E2E
            {!pureReady ? " (未配置)" : ""}
          </label>
          <label className={mode === "hybrid" ? "rtc-mode active" : "rtc-mode"}>
            <input
              type="radio"
              name="rtc-mode"
              value="hybrid"
              checked={mode === "hybrid"}
              disabled={disabled}
              onChange={() => onModeChange("hybrid")}
            />
            Soul 混合
            {!hybridReady ? " (需 tunnel)" : ""}
          </label>
        </div>
      ) : (
        <div className="rtc-live-status">
          <span className={`rtc-agent-badge phase-${agentPhase}`}>
            {agentPhaseLabel[agentPhase]}
          </span>
          <span className={`rtc-mic-badge${micActive ? " active" : ""}`}>
            {micActive ? "麦克风已开" : "麦克风未开"}
          </span>
          <span className="rtc-live-mode">{mode === "pure" ? "纯 E2E" : "Soul 混合"}</span>
        </div>
      )}

      {autoplayBlocked ? (
        <div className="rtc-autoplay-banner">
          <p>浏览器阻止了自动播放，点一下才能听到 Boxi。</p>
          <button type="button" onClick={() => void onResumeAudio()}>
            启用声音
          </button>
        </div>
      ) : null}

      {isLive ? (
        <RtcSubtitleList
          lines={subtitles}
          welcomeMessage={welcomeMessage}
          agentPhase={agentPhase}
        />
      ) : null}

      <div className="rtc-voice-actions">
        {!isLive ? (
          <button
            type="button"
            className="rtc-join-button"
            disabled={disabled || !modeReady}
            onClick={onJoin}
          >
            开始实时语音
          </button>
        ) : (
          <button type="button" className="rtc-leave-button" disabled={disabled} onClick={onLeave}>
            结束实时语音
          </button>
        )}
      </div>

      <div id="rtc-remote-player" className="rtc-remote-player" aria-hidden="true" />

      {error ? <p className="rtc-voice-error">{error}</p> : null}
    </div>
  );
}
