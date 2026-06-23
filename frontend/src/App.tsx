import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { BehaviorDecision } from "./api/behavior";
import {
  requestChatComplete,
  requestChatStream,
  type ChatCompleteResponse,
  type ChatTargetLanguage,
} from "./api/chat";
import { fetchStoredMessages } from "./api/messages";
import { avatarStates, stateLines, type AvatarState } from "./avatar/types";
import { useAvatarState } from "./avatar/useAvatarState";
import { useBehaviorTicks } from "./avatar/useBehaviorTicks";
import {
  PROACTIVE_ATTENTION_MS,
  proactiveAvatarHoldDuration,
  resolveBehaviorMessageId,
  shouldSkipDuplicateBehaviorMessage,
} from "./avatar/proactiveDelivery";
import { useMoodRest } from "./avatar/useMoodRest";
import {
  completionToTurnSummary,
  formatMessageMeta,
  formatUsd,
  restoreLastTurnFromMessages,
  storedMessageToChatMessage,
  streamMetaToMessageMeta,
  streamMetaToTurnSummary,
  type ChatMessage,
  type MessageMeta,
  type TurnSummary,
} from "./chat/types";
import { appendChatStreamDelta } from "./chat/streamRender";
import { PixelCharacter } from "./components/PixelCharacter";
import { RtcVoicePanel } from "./components/RtcVoicePanel";
import { LetterView } from "./letter/LetterView";
import { type LetterMood } from "./letter/scripts";
import { fetchMoodState } from "./api/mood";
import { MemoryLinksPanel } from "./components/MemoryLinksPanel";
import { MemoryPanel } from "./components/MemoryPanel";
import { MoodPanel } from "./components/MoodPanel";
import { RelationshipPanel } from "./components/RelationshipPanel";
import { primeAudioPlayback } from "./voice/audioUnlock";
import { usePushToTalk } from "./voice/usePushToTalk";
import { useTextToSpeech } from "./voice/useTextToSpeech";
import { useVoiceTranscript } from "./voice/useVoiceTranscript";
import { useRtcVoice } from "./rtc/useRtcVoice";
import type { RtcAgentPhase } from "./rtc/rtcMessages";

type ApiHealth = {
  status: "checking" | "ok" | "offline";
  detail: string;
  version?: string;
};

type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const showAvatarDebug =
  import.meta.env.DEV || import.meta.env.VITE_SHOW_AVATAR_DEBUG === "1";
const CHAT_VIEW_CLEARED_KEY = "cyber-companion-chat-view-cleared";
const TARGET_LANGUAGE_KEY = "cyber-companion-target-language";

type TargetLanguageSetting = "off" | ChatTargetLanguage;

function isTargetLanguageSetting(value: string | null): value is TargetLanguageSetting {
  return value === "off" || value === "en" || value === "ja";
}

function nextTargetLanguage(current: TargetLanguageSetting): TargetLanguageSetting {
  if (current === "off") return "en";
  if (current === "en") return "ja";
  return "off";
}

function targetLanguageLabel(setting: TargetLanguageSetting): string {
  if (setting === "off") return "译文";
  return setting === "en" ? "译文 EN" : "译文 JA";
}

const _LEADING_FISH_TAGS_RE = /^(\[[^\]]+\]\s*)+/;
function stripLeadingFishTags(text: string): string {
  return text.replace(_LEADING_FISH_TAGS_RE, "");
}

function completionToMessageMeta(completion: ChatCompleteResponse): MessageMeta {
  return {
    provider: completion.provider,
    model: completion.model,
    mock: completion.mock,
    decision: completion.decision,
    shouldCallLlm: completion.should_call_llm,
    usage: completion.usage,
    cost: completion.cost,
  };
}

function completionToFetchResult(completion: ChatCompleteResponse) {
  return {
    replyText: completion.content,
    avatarState: parseAvatarState(completion.avatar_state),
    meta: completionToMessageMeta(completion),
    translation: completion.translation ?? undefined,
  };
}

function parseAvatarState(value: string): AvatarState {
  if ((avatarStates as readonly string[]).includes(value)) {
    return value as AvatarState;
  }

  return "talking";
}

function App() {
  const [uiMode, setUiMode] = useState<"classic" | "letter">("classic");
  const [letterMood, setLetterMood] = useState<LetterMood | undefined>(undefined);
  const [targetLanguage, setTargetLanguage] = useState<TargetLanguageSetting>(() => {
    const stored = localStorage.getItem(TARGET_LANGUAGE_KEY);
    return isTargetLanguageSetting(stored) ? stored : "off";
  });
  const targetLanguageRef = useRef(targetLanguage);
  targetLanguageRef.current = targetLanguage;

  const cycleTargetLanguage = useCallback(() => {
    setTargetLanguage((current) => {
      const next = nextTargetLanguage(current);
      localStorage.setItem(TARGET_LANGUAGE_KEY, next);
      return next;
    });
  }, []);
  const [pipecatStatus, setPipecatStatus] = useState<"stopped" | "running" | "loading" | "error">("stopped");
  const pipecatStatusRef = useRef(pipecatStatus);
  pipecatStatusRef.current = pipecatStatus;

  const togglePipecat = async () => {
    const current = pipecatStatusRef.current;
    if (current === "loading") return;
    setPipecatStatus("loading");
    const isRunning = current === "running";
    try {
      const endpoint = isRunning ? "/realtime/stop" : "/realtime/start";
      await fetch(`${apiBaseUrl}${endpoint}`, { method: "POST" });
      setPipecatStatus(isRunning ? "stopped" : "running");
    } catch {
      setPipecatStatus("error");
    }
  };
  const pipecatTranscript = useVoiceTranscript(pipecatStatus === "running", apiBaseUrl);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const lastBoxiText = useMemo(
    () => [...messages].reverse().find((m) => m.speaker === "boxi")?.text,
    [messages],
  );
  const [historyStatus, setHistoryStatus] = useState<"loading" | "ready" | "offline">("loading");
  const [isSending, setIsSending] = useState(false);
  const [lastTurn, setLastTurn] = useState<TurnSummary | null>(null);
  const [chatViewCleared, setChatViewCleared] = useState(
    () => sessionStorage.getItem(CHAT_VIEW_CLEARED_KEY) === "1",
  );
  const [proactiveAttention, setProactiveAttention] = useState(false);
  const [proactiveAttentionMessageId, setProactiveAttentionMessageId] = useState<number | null>(
    null,
  );
  const [apiHealth, setApiHealth] = useState<ApiHealth>({
    status: "checking",
    detail: "checking local API",
  });
  const applyRestStateRef = useRef<(rest?: AvatarState) => void>(() => {});
  const returnToRestStateRef = useRef<() => void>(() => {});
  const moodRest = useMoodRest({
    enabled: apiHealth.status === "ok",
    onMoodRestUpdated: (restState) => applyRestStateRef.current(restState),
  });
  const {
    avatarState,
    setManualState,
    runChatFetchSequence,
    runEmptySubmitSequence,
    scheduleReturnToIdle,
    scheduleReturnForMs,
    cancelScheduledReturn,
    returnToRestState,
    applyRestStateIfResting,
  } = useAvatarState("idle", moodRest.getRestState);
  applyRestStateRef.current = applyRestStateIfResting;
  returnToRestStateRef.current = returnToRestState;
  const messageListRef = useRef<HTMLDivElement>(null);
  const proactiveAttentionTimerRef = useRef<number | null>(null);
  const lastProactiveScrollRef = useRef<number | null>(null);
  const nextMessageIdRef = useRef(1);
  const chatEpochRef = useRef(0);
  const ttsEpochRef = useRef(0);
  const ttsEnabledRef = useRef(false);
  const ttsMutedRef = useRef(false);
  const ttsActiveRef = useRef(false);
  const speakReplyRef = useRef<
    (input: { text: string; decision?: string; avatarState?: string; userMessage?: string }) => Promise<boolean>
  >(async () => false);
  const stopSpeakingRef = useRef<(notifyEnd?: boolean) => void>(() => {});
  const markBehaviorActivityRef = useRef(() => {});

  const statusText = useMemo(() => stateLines[avatarState], [avatarState]);

  const allocateMessageId = () => {
    const id = nextMessageIdRef.current;
    nextMessageIdRef.current += 1;
    return id;
  };

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = (await response.json()) as HealthResponse;

        if (!active) {
          return;
        }

        setApiHealth({
          status: data.status === "ok" ? "ok" : "offline",
          detail: data.service,
          version: data.version,
        });
      } catch (error) {
        if (!active) {
          return;
        }

        setApiHealth({
          status: "offline",
          detail: error instanceof Error ? error.message : "unreachable",
        });
        setHistoryStatus("offline");
        return;
      }

      try {
        const skipHistoryRestore = sessionStorage.getItem(CHAT_VIEW_CLEARED_KEY) === "1";
        if (!skipHistoryRestore) {
          const stored = await fetchStoredMessages();
          if (!active) {
            return;
          }

          const restored = stored
            .map(storedMessageToChatMessage)
            .filter((message): message is ChatMessage => message !== null);

          setMessages(restored);
          nextMessageIdRef.current =
            restored.reduce((maxId, message) => Math.max(maxId, message.id), 0) + 1;
          const restoredLastTurn = restoreLastTurnFromMessages(restored);
          if (restoredLastTurn) {
            setLastTurn(restoredLastTurn);
          }
        }
        if (!active) {
          return;
        }

        setHistoryStatus("ready");
      } catch {
        if (!active) {
          return;
        }

        setHistoryStatus("offline");
      }
    }

    void bootstrap();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (uiMode !== "letter") {
      setLetterMood(undefined);
      return;
    }

    let active = true;

    async function loadLetterMood() {
      try {
        const state = await fetchMoodState();
        if (!active) return;
        // TODO: refine mapping once mood vocabulary stabilizes
        let mapped: LetterMood;
        if (state.mood === "sad" || state.mood === "worried" || state.mood === "angry") {
          mapped = "fragile";
        } else if (state.mood === "happy") {
          mapped = "excited";
        } else if (state.mood === "annoyed") {
          mapped = "hesitant";
        } else {
          mapped = "calm";
        }
        setLetterMood(mapped);
      } catch {
        // backend offline — LetterView falls back to internal picker
      }
    }

    void loadLetterMood();
    return () => {
      active = false;
    };
  }, [uiMode]);

  useEffect(() => {
    const messageList = messageListRef.current;

    if (!messageList) {
      return;
    }

    messageList.scrollTop = messageList.scrollHeight;
  }, [messages]);

  useEffect(() => {
    const lastProactive = [...messages].reverse().find((message) => message.initiation === "proactive");
    if (!lastProactive || lastProactive.id === lastProactiveScrollRef.current) {
      return;
    }

    lastProactiveScrollRef.current = lastProactive.id;
    requestAnimationFrame(() => {
      const target = messageListRef.current?.querySelector(
        `[data-message-id="${lastProactive.id}"]`,
      );
      target?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }, [messages]);

  useEffect(() => {
    return () => {
      if (proactiveAttentionTimerRef.current !== null) {
        window.clearTimeout(proactiveAttentionTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const verifyWindow = window as Window & {
      __uiVerify?: {
        refreshMoodRest?: () => Promise<string>;
        returnToRestState?: () => void;
        getAvatarStateLabel?: () => string;
        triggerProactiveCheck?: (force?: boolean) => Promise<BehaviorDecision>;
        handleBehaviorDecision?: (decision: BehaviorDecision) => Promise<void>;
      };
    };

    verifyWindow.__uiVerify = {
      ...verifyWindow.__uiVerify,
      refreshMoodRest: async () => {
        const restState = await moodRest.refreshMood();
        return restState;
      },
      returnToRestState: () => returnToRestStateRef.current(),
      getAvatarStateLabel: () =>
        document.querySelector(".state-label")?.textContent?.trim() ?? "",
      triggerProactiveCheck: async (force = true) => {
        const { evaluateBehavior } = await import("./api/behavior");
        return evaluateBehavior("proactive_check", "", { forceProactive: force });
      },
    };
  }, [moodRest.refreshMood]);

  const clearChatView = useCallback(() => {
    setMessages([]);
    setLastTurn(null);
    nextMessageIdRef.current = 1;
    sessionStorage.setItem(CHAT_VIEW_CLEARED_KEY, "1");
    setChatViewCleared(true);
  }, []);

  async function submitToBackend(userText: string, appendUserBubble: boolean) {
    primeAudioPlayback();
    markBehaviorActivityRef.current();
    if (userText.trim()) {
      sessionStorage.removeItem(CHAT_VIEW_CLEARED_KEY);
      setChatViewCleared(false);
    }
    const turnEpoch = chatEpochRef.current + 1;
    chatEpochRef.current = turnEpoch;
    ttsActiveRef.current = false;
    stopSpeakingRef.current(false);
    const userMessageId = appendUserBubble ? allocateMessageId() : null;

    if (appendUserBubble && userMessageId !== null) {
      setMessages((current) => [
        ...current,
        { id: userMessageId, speaker: "user", text: userText },
      ]);
    }

    setIsSending(true);

    try {
      await runChatFetchSequence(
        async () => {
          const boxiMessageId = allocateMessageId();

          const tryStream = async () => {
            const streamEpoch = turnEpoch;

            setMessages((current) => [
              ...current,
              { id: boxiMessageId, speaker: "boxi", text: "" },
            ]);

            let sawFirstDelta = false;

            const streamRequestLanguage =
              targetLanguageRef.current === "off" ? undefined : targetLanguageRef.current;

            const streamResult = await requestChatStream(
              userText,
              {
                onDelta: (delta) => {
                  if (streamEpoch !== chatEpochRef.current) {
                    return;
                  }

                  if (!sawFirstDelta) {
                    sawFirstDelta = true;
                    cancelScheduledReturn();
                    setManualState("talking");
                  }

                  setMessages((current) => appendChatStreamDelta(current, boxiMessageId, delta));
                },
                onDone: (meta) => {
                  setLastTurn(streamMetaToTurnSummary(meta));
                  const finalText =
                    typeof meta.content === "string" && meta.content.length > 0
                      ? meta.content
                      : undefined;
                  setMessages((current) =>
                    current.map((message) =>
                      message.id === boxiMessageId
                        ? {
                            ...message,
                            text: finalText ?? message.text,
                            meta: streamMetaToMessageMeta(meta),
                            translation: meta.translation ?? undefined,
                          }
                        : message,
                    ),
                  );
                },
                onError: () => {},
              },
              streamRequestLanguage,
            );

            return {
              ...completionToFetchResult({
                provider: streamResult.meta.provider,
                model: streamResult.meta.model,
                content: streamResult.content,
                usage: streamResult.meta.usage,
                cost: streamResult.meta.cost,
                mock: streamResult.meta.provider === "mock",
                avatar_state: streamResult.meta.avatar_state,
                decision: streamResult.meta.decision,
                should_call_llm: streamResult.meta.should_call_llm,
                translation: streamResult.meta.translation,
              }),
              streamed: true,
            };
          };

          try {
            return await tryStream();
          } catch (error) {
            ttsActiveRef.current = false;
            stopSpeakingRef.current(false);
            setMessages((current) => current.filter((message) => message.id !== boxiMessageId));

            if (error instanceof DOMException && error.name === "AbortError") {
              throw error;
            }

            const fallbackLanguage =
              targetLanguageRef.current === "off" ? undefined : targetLanguageRef.current;
            const completion = await requestChatComplete(userText, fallbackLanguage);
            setLastTurn(completionToTurnSummary(completion));
            return completionToFetchResult(completion);
          }
        },
        async (result) => {
          if (turnEpoch !== chatEpochRef.current) {
            return;
          }

          if (!result.replyText.trim()) {
            return;
          }

          if (!result.streamed) {
            setMessages((current) => [
              ...current,
              {
                id: allocateMessageId(),
                speaker: "boxi",
                text: result.replyText,
                meta: result.meta as MessageMeta | undefined,
                translation: result.translation,
              },
            ]);
          }

          const shouldAttemptTts =
            ttsEnabledRef.current && !ttsMutedRef.current && Boolean(result.replyText.trim());
          if (!shouldAttemptTts) {
            return;
          }

          const decision =
            typeof result.meta?.decision === "string" ? result.meta.decision : undefined;

          // speakReply returns false when TTS is disabled, muted, or skipped by
          // policy. In every "did not speak" case we must still hand the avatar
          // back to idle ourselves, or it gets stuck in the `thinking` state set
          // at the start of this turn.
          const spoke = await speakReplyRef.current({
            text: result.replyText,
            decision,
            avatarState: result.avatarState,
            userMessage: userText,
          });

          if (!spoke) {
            ttsActiveRef.current = false;
          }

          if (!spoke && turnEpoch === chatEpochRef.current) {
            scheduleReturnToIdle(result.avatarState ?? "talking", result.replyText);
          }

          return { deferIdleFallback: true };
        },
      );
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      const fallback =
        apiHealth.status === "offline"
          ? "本地 API 没连上。我在盒子里喊了，外面装没听见。"
          : `provider 调用失败了：${detail}`;

      setMessages((current) => [
        ...current,
        {
          id: allocateMessageId(),
          speaker: "boxi",
          text: fallback,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  const submitFromVoice = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) {
        return;
      }

      setDraft("");
      await submitToBackend(trimmed, true);
    },
    [isSending],
  );

  const {
    enabled: ttsEnabled,
    muted: ttsMuted,
    speaking: ttsSpeaking,
    providerName: ttsProviderName,
    forceMock: ttsForceMock,
    lastError: ttsLastError,
    toggleMuted: toggleTtsMuted,
    speakReply,
    stopSpeaking,
  } = useTextToSpeech({
    onSpeakingStart: () => {
      ttsEpochRef.current = chatEpochRef.current;
      ttsActiveRef.current = true;
      cancelScheduledReturn();
      setManualState("talking");
    },
    onSpeakingEnd: () => {
      ttsActiveRef.current = false;
      if (ttsEpochRef.current !== chatEpochRef.current) {
        return;
      }

      returnToRestStateRef.current();
    },
  });

  ttsEnabledRef.current = ttsEnabled;
  ttsMutedRef.current = ttsMuted;
  speakReplyRef.current = speakReply;
  stopSpeakingRef.current = stopSpeaking;

  const triggerProactiveAttention = useCallback((messageId: number) => {
    if (proactiveAttentionTimerRef.current !== null) {
      window.clearTimeout(proactiveAttentionTimerRef.current);
    }

    setProactiveAttention(true);
    setProactiveAttentionMessageId(messageId);
    proactiveAttentionTimerRef.current = window.setTimeout(() => {
      setProactiveAttention(false);
      setProactiveAttentionMessageId(null);
      proactiveAttentionTimerRef.current = null;
    }, PROACTIVE_ATTENTION_MS);
  }, []);

  const handleBehaviorDecision = useCallback(
    async (decision: BehaviorDecision) => {
      const avatar = parseAvatarState(decision.avatar_state);
      const localLine = decision.local_response?.trim() ?? "";

      if (decision.decision === "proactive" && localLine) {
        chatEpochRef.current += 1;
        const messageId = resolveBehaviorMessageId(
          decision.saved_message_id,
          allocateMessageId,
        );
        if (typeof decision.saved_message_id === "number") {
          nextMessageIdRef.current = Math.max(nextMessageIdRef.current, messageId + 1);
        }

        let appended = false;
        setMessages((current) => {
          if (shouldSkipDuplicateBehaviorMessage(current, messageId)) {
            return current;
          }

          appended = true;
          return [
            ...current,
            {
              id: messageId,
              speaker: "boxi",
              text: localLine,
              meta: {
                decision: decision.decision,
                shouldCallLlm: decision.should_call_llm,
              },
              initiation: "proactive",
            },
          ];
        });

        if (!appended) {
          return;
        }

        triggerProactiveAttention(messageId);
        cancelScheduledReturn();
        setManualState(avatar);
        scheduleReturnForMs(avatar, proactiveAvatarHoldDuration(avatar, localLine));

        const shouldAttemptTts = ttsEnabledRef.current && !ttsMutedRef.current;
        if (!shouldAttemptTts) {
          return;
        }

        const spoke = await speakReplyRef.current({
          text: localLine,
          decision: decision.decision,
          avatarState: decision.avatar_state,
        });
        if (!spoke) {
          scheduleReturnForMs(avatar, proactiveAvatarHoldDuration(avatar, localLine));
        }
        return;
      }

      if (decision.decision === "mutter" && localLine) {
        chatEpochRef.current += 1;
        const messageId = resolveBehaviorMessageId(
          decision.saved_message_id,
          allocateMessageId,
        );
        if (typeof decision.saved_message_id === "number") {
          nextMessageIdRef.current = Math.max(nextMessageIdRef.current, messageId + 1);
        }

        setMessages((current) => {
          if (shouldSkipDuplicateBehaviorMessage(current, messageId)) {
            return current;
          }

          return [
            ...current,
            {
              id: messageId,
              speaker: "boxi",
              text: localLine,
              meta: { decision: decision.decision },
            },
          ];
        });
        cancelScheduledReturn();
        setManualState(avatar);

        const shouldAttemptTts = ttsEnabledRef.current && !ttsMutedRef.current;
        if (shouldAttemptTts) {
          const spoke = await speakReplyRef.current({
            text: localLine,
            decision: decision.decision,
            avatarState: decision.avatar_state,
          });
          if (!spoke) {
            scheduleReturnToIdle(avatar, localLine);
          }
          return;
        }

        scheduleReturnToIdle(avatar, localLine);
        return;
      }

      if (decision.decision === "observe") {
        cancelScheduledReturn();
        setManualState(avatar);
        if (avatar !== "idle") {
          scheduleReturnToIdle(avatar, "");
        }
      }
    },
    [
      cancelScheduledReturn,
      scheduleReturnForMs,
      scheduleReturnToIdle,
      setManualState,
      triggerProactiveAttention,
    ],
  );

  const { markUserActivity: markBehaviorActivity } = useBehaviorTicks({
    enabled: apiHealth.status === "ok",
    paused: isSending || ttsSpeaking || ttsActiveRef.current,
    onDecision: (decision) => {
      void handleBehaviorDecision(decision);
    },
  });
  markBehaviorActivityRef.current = markBehaviorActivity;

  useEffect(() => {
    const verifyWindow = window as Window & {
      __uiVerify?: {
        handleBehaviorDecision?: (decision: BehaviorDecision) => Promise<void>;
      };
    };

    verifyWindow.__uiVerify = {
      ...verifyWindow.__uiVerify,
      handleBehaviorDecision,
    };
  }, [handleBehaviorDecision]);

  const {
    enabled: pushToTalkEnabled,
    forceMock: sttForceMock,
    state: pushToTalkState,
    errorMessage: pushToTalkError,
    handlePointerDown: handlePttPointerDown,
    handlePointerUp: handlePttPointerUp,
    handlePointerLeave: handlePttPointerLeave,
    handlePointerCancel: handlePttPointerCancel,
    handleMouseDown: handlePttMouseDown,
    handleMouseUp: handlePttMouseUp,
    handleMouseLeave: handlePttMouseLeave,
  } = usePushToTalk({
    onTranscript: submitFromVoice,
  });

  const mapRtcAgentToAvatar = useCallback(
    (agentPhase: RtcAgentPhase) => {
      if (agentPhase === "speaking") {
        cancelScheduledReturn();
        setManualState("talking");
        return;
      }
      if (agentPhase === "thinking") {
        cancelScheduledReturn();
        setManualState("thinking");
        return;
      }
      if (agentPhase === "listening" || agentPhase === "idle") {
        scheduleReturnToIdle(avatarState, "");
      }
    },
    [avatarState, cancelScheduledReturn, scheduleReturnToIdle, setManualState],
  );

  const rtcVoice = useRtcVoice({
    onAgentPhaseChange: mapRtcAgentToAvatar,
  });

  const rtcPhaseLabel = useMemo(() => {
    switch (rtcVoice.phase) {
      case "joining":
        return "连接中…";
      case "live":
        return rtcVoice.mode === "pure" ? "纯 E2E 通话中" : "Soul 混合通话中";
      case "leaving":
        return "断开中…";
      case "error":
        return "RTC 错误";
      default:
        return "未连接";
    }
  }, [rtcVoice.mode, rtcVoice.phase]);

  const voiceStatusText = useMemo(() => {
    if (pushToTalkState === "recording") {
      return "Recording… release to transcribe";
    }

    if (pushToTalkState === "transcribing") {
      return "Transcribing voice input…";
    }

    if (pushToTalkError) {
      return pushToTalkError;
    }

    if (pushToTalkEnabled) {
      if (sttForceMock) {
        return "Hold the mic button (≥0.5s). STT is mock — placeholder text only, not your words.";
      }

      return "Hold the mic button (≥0.5s). First transcription may be slow while the Whisper model loads.";
    }

    if (apiHealth.status !== "ok") {
      return "Voice input needs the local API. Restart with npm run dev (backend must be running on :8000).";
    }

    return null;
  }, [apiHealth.status, pushToTalkEnabled, pushToTalkError, pushToTalkState, sttForceMock]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    primeAudioPlayback();
    const text = draft.trim();

    if (isSending) {
      return;
    }

    if (!text) {
      if (apiHealth.status === "offline") {
        runEmptySubmitSequence();
        return;
      }

      await submitToBackend("", false);
      return;
    }

    setDraft("");
    await submitToBackend(text, true);
  }

  return (
    <main className="app-shell">
      <section className="companion-panel" aria-label="Cyber Companion">
        <div className="status-strip">
          <span className="status-dot" aria-hidden="true" />
          <span>Boxi</span>
          {proactiveAttention ? (
            <span className="proactive-attention-dot" aria-label="Boxi reached out" />
          ) : null}
          <span className="state-label">{avatarState}</span>
        </div>

        <PixelCharacter state={avatarState} attentionPulse={proactiveAttention} />

        <p className="status-line">{statusText}</p>

        <RtcVoicePanel
          mode={rtcVoice.mode}
          onModeChange={rtcVoice.setMode}
          modeReady={rtcVoice.modeReady}
          pureReady={rtcVoice.status?.pure_ready ?? false}
          hybridReady={rtcVoice.status?.hybrid_ready ?? false}
          phaseLabel={rtcPhaseLabel}
          agentPhase={rtcVoice.agentPhase}
          error={rtcVoice.error}
          isLive={rtcVoice.isLive}
          subtitles={rtcVoice.subtitles}
          welcomeMessage={rtcVoice.session?.welcome_message}
          autoplayBlocked={rtcVoice.autoplayBlocked}
          micActive={rtcVoice.micActive}
          onJoin={() => {
            primeAudioPlayback();
            void rtcVoice.join();
          }}
          onLeave={() => void rtcVoice.leave()}
          onResumeAudio={() => void rtcVoice.resumeAutoplay()}
          disabled={apiHealth.status !== "ok"}
          vikingMemoryEnabled={rtcVoice.status?.viking_memory_enabled ?? false}
          vikingMemoryWriteReady={rtcVoice.status?.viking_memory_write_ready ?? false}
          vikingUserId={rtcVoice.status?.default_user_id}
          vikingMemorySaveState={rtcVoice.memorySaveState}
          sqliteMemoryReady={rtcVoice.status?.sqlite_memory_ready ?? false}
        />

        {!rtcVoice.isLive ? (
          <>
            <RelationshipPanel enabled={apiHealth.status === "ok"} />
            <MoodPanel enabled={apiHealth.status === "ok"} />
            <MemoryPanel enabled={apiHealth.status === "ok"} />
            <MemoryLinksPanel enabled={apiHealth.status === "ok"} />
          </>
        ) : null}

        {showAvatarDebug ? (
          <details className="state-debug" open>
            <summary>Avatar debug</summary>
            <div className="state-controls" aria-label="Avatar state controls">
              {avatarStates.map((state) => (
                <button
                  key={state}
                  className={state === avatarState ? "state-button active" : "state-button"}
                  type="button"
                  onClick={() => setManualState(state as AvatarState)}
                >
                  {state}
                </button>
              ))}
            </div>
          </details>
        ) : null}
      </section>

      <section
        className={proactiveAttention ? "chat-panel proactive-attention" : "chat-panel"}
        aria-label="Chat"
      >
        <div className="chat-header">
          <div>
            <h1>Cyber Companion</h1>
            <p>Text MVP</p>
          </div>
          <div className={`api-status ${apiHealth.status}`} aria-live="polite">
            <span>API</span>
            <strong>{apiHealth.status}</strong>
            <small>{apiHealth.version ? `v${apiHealth.version}` : apiHealth.detail}</small>
          </div>
          <div className="chat-header-actions">
            <button
              type="button"
              className={pipecatStatus === "running" ? "letter-toggle-button active" : "letter-toggle-button"}
              onClick={() => void togglePipecat()}
              disabled={pipecatStatus === "loading" || apiHealth.status !== "ok"}
              title="Pipecat 本地语音（麦克风 + 扬声器）"
            >
              {pipecatStatus === "loading" ? "…" : pipecatStatus === "running" ? "Pipecat 开" : pipecatStatus === "error" ? "Pipecat ✗" : "Pipecat"}
            </button>
            <button
              type="button"
              className={uiMode === "letter" ? "letter-toggle-button active" : "letter-toggle-button"}
              onClick={() => setUiMode(uiMode === "classic" ? "letter" : "classic")}
              title="切换信笺模式"
            >
              {uiMode === "letter" ? "信笺" : "对话"}
            </button>
            <button
              type="button"
              className={targetLanguage === "off" ? "letter-toggle-button" : "letter-toggle-button active"}
              onClick={cycleTargetLanguage}
              title="给 Boxi 的回复加英文/日文译文（只影响之后的新消息）"
            >
              {targetLanguageLabel(targetLanguage)}
            </button>
            <button
              type="button"
              className="clear-chat-button"
              onClick={clearChatView}
              disabled={isSending || messages.length === 0}
              title="只清空当前对话框显示，不删除后端记忆"
            >
              清空对话
            </button>
            {ttsEnabled ? (
              <button
                type="button"
                className={ttsMuted ? "tts-toggle muted" : "tts-toggle"}
                aria-pressed={ttsMuted}
                onClick={toggleTtsMuted}
                title={
                  ttsForceMock
                    ? "TTS forced to silent mock by CYBER_COMPANION_TTS_MODE=mock"
                    : `TTS provider: ${ttsProviderName ?? "unknown"}`
                }
              >
                {ttsMuted ? "TTS off" : ttsSpeaking ? "Speaking" : "TTS on"}
              </button>
            ) : null}
          </div>
        </div>

        {lastTurn ? (
          <div className="turn-meta" aria-live="polite">
            <span>
              Last turn: {lastTurn.provider}/{lastTurn.model}
            </span>
            <span>
              {lastTurn.usage.total_tokens} tok · {formatUsd(lastTurn.cost.total_usd)}
            </span>
            <span>
              {lastTurn.decision}
              {lastTurn.mock ? " · mock" : ""}
              {!lastTurn.shouldCallLlm ? " · local" : ""}
            </span>
          </div>
        ) : null}

        {uiMode === "letter" ? (
          <LetterView mood={letterMood} text={lastBoxiText} />
        ) : (
          <>
            {pipecatStatus === "running" ? (
              <div className="pipecat-transcript" aria-live="polite">
                {pipecatTranscript.length === 0 ? (
                  <p className="chat-empty">Pipecat 字幕：等待你说话…</p>
                ) : (
                  pipecatTranscript.map((entry, index) => (
                    <article key={`${entry.ts}-${index}`} className={`message ${entry.role}`}>
                      <span className="speaker">{entry.role === "boxi" ? "Boxi" : "You"}</span>
                      <p>{entry.text}</p>
                    </article>
                  ))
                )}
              </div>
            ) : null}
            <div className="message-list" ref={messageListRef}>
              {historyStatus === "loading" ? (
                <p className="chat-empty">Loading chat history...</p>
              ) : null}
              {historyStatus !== "loading" && messages.length === 0 ? (
                <p className="chat-empty">
                  {chatViewCleared
                    ? "对话框已清空。记忆仍保留在本地；新开标签页可重新看到历史。"
                    : "还没有聊天记录。可以先扔一句话进来。"}
                </p>
              ) : null}
              {messages.map((message) => {
                const metaLine = message.meta ? formatMessageMeta(message.meta) : null;
                const messageClassName = [
                  "message",
                  message.speaker,
                  message.initiation === "proactive" ? "initiation-proactive" : "",
                  message.id === proactiveAttentionMessageId && proactiveAttention
                    ? "attention-cue"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ");

                return (
                  <article
                    key={message.id}
                    data-message-id={message.id}
                    className={messageClassName}
                  >
                    <span className="speaker">{message.speaker === "boxi" ? "Boxi" : "You"}</span>
                    <p>{message.text}</p>
                    {message.translation ? (
                      <p className="message-translation">{message.translation}</p>
                    ) : null}
                    {metaLine ? <p className="message-meta">{metaLine}</p> : null}
                  </article>
                );
              })}
            </div>

            <form className={`chat-form${pushToTalkEnabled ? " with-ptt" : ""}`} onSubmit={handleSubmit}>
              <label className="sr-only" htmlFor="chat-input">
                Message
              </label>
              <input
                id="chat-input"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Type something..."
                disabled={isSending || pushToTalkState === "transcribing"}
              />
              {pushToTalkEnabled && !rtcVoice.isLive ? (
                <button
                  type="button"
                  className={
                    pushToTalkState === "recording" ? "ptt-button recording" : "ptt-button"
                  }
                  aria-pressed={pushToTalkState === "recording"}
                  aria-label="Hold to talk"
                  disabled={isSending || pushToTalkState === "transcribing" || rtcVoice.isLive}
                  onPointerDown={handlePttPointerDown}
                  onPointerUp={handlePttPointerUp}
                  onPointerLeave={handlePttPointerLeave}
                  onPointerCancel={handlePttPointerCancel}
                  onMouseDown={handlePttMouseDown}
                  onMouseUp={handlePttMouseUp}
                  onMouseLeave={handlePttMouseLeave}
                >
                  {pushToTalkState === "recording"
                    ? "Rec"
                    : pushToTalkState === "transcribing"
                      ? "..."
                      : "Hold"}
                </button>
              ) : null}
              <button type="submit" disabled={isSending || pushToTalkState === "transcribing"}>
                {isSending ? "..." : "Send"}
              </button>
            </form>
          </>
        )}

        {voiceStatusText || ttsLastError ? (
          <p
            className={`voice-status${pushToTalkState === "recording" ? " recording" : ""}${
              pushToTalkError || ttsLastError ? " error" : ""
            }`}
            aria-live="polite"
          >
            {ttsLastError ?? voiceStatusText}
          </p>
        ) : null}
      </section>
    </main>
  );
}

export default App;
