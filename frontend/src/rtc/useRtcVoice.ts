import { useCallback, useEffect, useRef, useState } from "react";
import VERTC, { MediaType, RoomProfileType, StreamIndex } from "@volcengine/rtc";
import {
  fetchRtcStatus,
  postRtcTurn,
  prepareRtcSession,
  saveRtcMemorySession,
  startRtcAgent,
  stopRtcSession,
  type RtcMode,
  type RtcPrepareResponse,
  type RtcStatus,
} from "./api";
import {
  createRtcMessageState,
  detectCompletedTurn,
  parseRtcRoomMessage,
  type RtcAgentPhase,
  type RtcMessageState,
  type RtcSubtitleLine,
} from "./rtcMessages";
import type { VikingMemorySaveState } from "./vikingMemoryBadge";

export type RtcVoicePhase = "idle" | "joining" | "live" | "leaving" | "error";

const REMOTE_PLAYER_ID = "rtc-remote-player";

export type UseRtcVoiceOptions = {
  onAgentPhaseChange?: (phase: RtcAgentPhase) => void;
};

async function tryEnableAiDenoise(engine: Awaited<ReturnType<typeof VERTC.createEngine>>) {
  try {
    const mod = await import("@volcengine/rtc/extension-ainr");
    const extension = new mod.default();
    await engine.registerExtension(extension);
    extension.enable();
  } catch {
    // optional — demo ignores when unsupported
  }
}

export function useRtcVoice({ onAgentPhaseChange }: UseRtcVoiceOptions = {}) {
  const [status, setStatus] = useState<RtcStatus | null>(null);
  const [phase, setPhase] = useState<RtcVoicePhase>("idle");
  const [mode, setMode] = useState<RtcMode>("pure");
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<RtcPrepareResponse | null>(null);
  const [subtitles, setSubtitles] = useState<RtcSubtitleLine[]>([]);
  const [agentPhase, setAgentPhase] = useState<RtcAgentPhase>("idle");
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);
  const [micActive, setMicActive] = useState(false);
  const [memorySaveState, setMemorySaveState] = useState<VikingMemorySaveState>("idle");

  const engineRef = useRef<Awaited<ReturnType<typeof VERTC.createEngine>> | null>(null);
  const memorySaveTimerRef = useRef<number | null>(null);
  const sessionRef = useRef<RtcPrepareResponse | null>(null);
  const modeRef = useRef<RtcMode>("pure");
  const messageStateRef = useRef<RtcMessageState>(createRtcMessageState());
  const postedTurnKeysRef = useRef<Set<string>>(new Set());
  const tearingDownRef = useRef(false);

  const applyAgentPhase = useCallback(
    (next: RtcAgentPhase) => {
      setAgentPhase(next);
      onAgentPhaseChange?.(next);
    },
    [onAgentPhaseChange],
  );

  const clearMemorySaveTimer = useCallback(() => {
    if (memorySaveTimerRef.current !== null) {
      window.clearTimeout(memorySaveTimerRef.current);
      memorySaveTimerRef.current = null;
    }
  }, []);

  const flashMemorySaved = useCallback(() => {
    clearMemorySaveTimer();
    setMemorySaveState("saved");
    memorySaveTimerRef.current = window.setTimeout(() => {
      setMemorySaveState("idle");
      memorySaveTimerRef.current = null;
    }, 4000);
  }, [clearMemorySaveTimer]);

  useEffect(() => {
    return () => {
      clearMemorySaveTimer();
    };
  }, [clearMemorySaveTimer]);

  useEffect(() => {
    let active = true;
    void fetchRtcStatus()
      .then((value) => {
        if (active) {
          setStatus(value);
        }
      })
      .catch((fetchError: unknown) => {
        if (active) {
          setStatus(null);
          setError(fetchError instanceof Error ? fetchError.message : "RTC status unavailable");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const resetConversation = useCallback(() => {
    messageStateRef.current = createRtcMessageState();
    postedTurnKeysRef.current = new Set();
    setSubtitles([]);
    applyAgentPhase("idle");
    setAutoplayBlocked(false);
    setMicActive(false);
  }, [applyAgentPhase]);

  const maybePostCompletedTurn = useCallback((state: RtcMessageState) => {
    const current = sessionRef.current;
    if (!current) {
      return;
    }
    const completed = detectCompletedTurn(state.lines);
    if (!completed || postedTurnKeysRef.current.has(completed.turnKey)) {
      return;
    }
    postedTurnKeysRef.current.add(completed.turnKey);
    postRtcTurn({
      room_id: current.room_id,
      user_id: current.user_id,
      user_text: completed.userText,
      bot_text: completed.botText,
    });
  }, []);

  const startLocalMicrophone = useCallback(
    async (engine: Awaited<ReturnType<typeof VERTC.createEngine>>) => {
      const devices = await VERTC.enableDevices({ video: false, audio: true });
      if (!devices.audio) {
        throw new Error("麦克风权限被拒绝，请在浏览器设置里允许麦克风");
      }

      const inputs = await VERTC.enumerateAudioCaptureDevices();
      const mic = inputs.find(
        (device) => device.deviceId && (!device.kind || device.kind === "audioinput"),
      );
      if (!mic?.deviceId) {
        throw new Error("未找到可用麦克风设备");
      }

      // Match rtc-aigc-demo switchMic: publish first, then start capture.
      engine.publishStream(MediaType.AUDIO);
      await engine.startAudioCapture(mic.deviceId);
      engine.setCaptureVolume(StreamIndex.STREAM_INDEX_MAIN, 100);
      setMicActive(true);
    },
    [],
  );

  const teardownEngine = useCallback(async () => {
    const engine = engineRef.current;
    if (!engine) {
      return;
    }

    tearingDownRef.current = true;
    try {
      try {
        await engine.stopAudioCapture();
      } catch {
        // best-effort
      }
      try {
        await engine.unpublishStream(MediaType.AUDIO);
      } catch {
        // best-effort
      }
      try {
        await engine.leaveRoom();
      } catch {
        // best-effort
      }
    } finally {
      VERTC.destroyEngine(engine);
      engineRef.current = null;
      tearingDownRef.current = false;
    }
  }, []);

  const leave = useCallback(
    async (options?: { silent?: boolean }) => {
      const current = sessionRef.current;
      if (!current) {
        await teardownEngine();
        return;
      }

      if (!options?.silent) {
        setPhase("leaving");
        setError(null);
      }

      const transcript = messageStateRef.current.lines
        .filter((line) => line.text.trim())
        .map((line) => ({ speaker: line.speaker, text: line.text }));

      await teardownEngine();

      if (transcript.length > 0) {
        try {
          const latest = await fetchRtcStatus();
          setStatus(latest);
          if (latest.viking_memory_write_ready) {
            setMemorySaveState("saving");
            await saveRtcMemorySession({
              room_id: current.room_id,
              user_id: current.user_id,
              bot_user_id: current.bot_user_id,
              subtitles: transcript,
            });
            flashMemorySaved();
          }
        } catch (memoryError: unknown) {
          setMemorySaveState("idle");
          if (!options?.silent) {
            const message =
              memoryError instanceof Error ? memoryError.message : "RTC memory save failed";
            setError(message);
            setPhase("error");
            return;
          }
        }
      }

      try {
        await stopRtcSession(modeRef.current, current.room_id);
      } catch (leaveError: unknown) {
        if (!options?.silent) {
          setError(leaveError instanceof Error ? leaveError.message : "RTC leave failed");
          setPhase("error");
        }
        return;
      }

      sessionRef.current = null;
      setSession(null);
      resetConversation();
      setMicActive(false);
      if (!options?.silent) {
        setPhase("idle");
      }
    },
    [flashMemorySaved, resetConversation, teardownEngine],
  );

  const join = useCallback(async () => {
    setPhase("joining");
    setError(null);
    clearMemorySaveTimer();
    setMemorySaveState("idle");
    resetConversation();

    let prepared: RtcPrepareResponse | null = null;

    try {
      const latest = await fetchRtcStatus();
      setStatus(latest);
      const ready = mode === "pure" ? latest.pure_ready : latest.hybrid_ready;
      if (!ready) {
        const missing = mode === "pure" ? latest.missing_pure : latest.missing_hybrid;
        throw new Error(`RTC ${mode} not configured: ${missing.join(", ") || "missing env"}`);
      }

      const supported = await VERTC.isSupported();
      if (!supported) {
        throw new Error("Browser does not support Volcengine RTC");
      }

      const permission = await VERTC.enableDevices({ video: false, audio: true });
      if (!permission.audio) {
        throw new Error("麦克风权限被拒绝，请在浏览器设置里允许麦克风");
      }

      prepared = await prepareRtcSession(mode);
      modeRef.current = mode;
      setMicActive(false);

      messageStateRef.current = {
        ...createRtcMessageState(),
        localUserId: prepared.user_id,
        botUserId: prepared.bot_user_id,
      };

      const engine = VERTC.createEngine(prepared.app_id);
      engineRef.current = engine;
      await tryEnableAiDenoise(engine);

      engine.on(VERTC.events.onUserPublishStream, (event) => {
        if (event.mediaType === MediaType.AUDIO || event.mediaType === MediaType.AUDIO_AND_VIDEO) {
          engine.setRemoteVideoPlayer(StreamIndex.STREAM_INDEX_MAIN, {
            userId: event.userId,
            renderDom: REMOTE_PLAYER_ID,
          });
        }
      });

      engine.on(VERTC.events.onRoomBinaryMessageReceived, (event) => {
        const prevPhase = messageStateRef.current.agentPhase;
        const next = parseRtcRoomMessage(event.message, messageStateRef.current);
        messageStateRef.current = next;
        setSubtitles(next.lines);
        maybePostCompletedTurn(next);
        if (next.agentPhase !== prevPhase) {
          applyAgentPhase(next.agentPhase);
        }
      });

      engine.on(VERTC.events.onAutoplayFailed, () => {
        setAutoplayBlocked(true);
      });

      engine.on(VERTC.events.onError, (event) => {
        if (tearingDownRef.current) {
          return;
        }
        const code = String(event.errorCode ?? "RTC error");
        if (code === "leave_room") {
          return;
        }
        if (code === "token_error" || code === "TOKEN_EXPIRED") {
          setError(
            "RTC Token 无效（token_error）。请确认 VOLC_RTC_APP_KEY 与控制台一致，并重新点「开始实时语音」。",
          );
        } else {
          setError(code);
        }
        setPhase("error");
      });

      await engine.joinRoom(
        prepared.token,
        prepared.room_id,
        {
          userId: prepared.user_id,
          extraInfo: JSON.stringify({
            call_scene: "cyber-companion",
            user_name: prepared.user_id,
            user_id: prepared.user_id,
          }),
        },
        {
          isAutoPublish: false,
          isAutoSubscribeAudio: true,
          roomProfileType: RoomProfileType.chat,
        },
      );

      await startLocalMicrophone(engine);

      const started = await startRtcAgent(mode, prepared.room_id, prepared.user_id);
      const liveSession = { ...prepared, welcome_message: started.welcome_message };
      messageStateRef.current = { ...messageStateRef.current, agentEnabled: true };

      sessionRef.current = liveSession;
      setSession(liveSession);
      setPhase("live");
    } catch (joinError: unknown) {
      sessionRef.current = null;
      setSession(null);
      await teardownEngine();
      if (prepared) {
        try {
          await stopRtcSession(modeRef.current, prepared.room_id);
        } catch {
          // best-effort cleanup if agent had started
        }
      }
      setError(joinError instanceof Error ? joinError.message : "RTC join failed");
      setPhase("error");
    }
  }, [
    applyAgentPhase,
    clearMemorySaveTimer,
    maybePostCompletedTurn,
    mode,
    resetConversation,
    startLocalMicrophone,
    teardownEngine,
  ]);

  const resumeAutoplay = useCallback(async () => {
    const engine = engineRef.current;
    const botId = sessionRef.current?.bot_user_id;
    if (!engine || !botId) {
      return;
    }
    try {
      await engine.play(botId);
      setAutoplayBlocked(false);
    } catch {
      setAutoplayBlocked(true);
    }
  }, []);

  useEffect(() => {
    const handleUnload = () => {
      void leave({ silent: true });
    };
    window.addEventListener("pagehide", handleUnload);
    return () => {
      window.removeEventListener("pagehide", handleUnload);
    };
  }, [leave]);

  const modeReady = mode === "pure" ? status?.pure_ready : status?.hybrid_ready;

  return {
    status,
    phase,
    mode,
    setMode,
    error,
    session,
    subtitles,
    agentPhase,
    autoplayBlocked,
    modeReady: Boolean(modeReady),
    join,
    leave,
    resumeAutoplay,
    micActive,
    isLive: phase === "live",
    memorySaveState,
  };
}
