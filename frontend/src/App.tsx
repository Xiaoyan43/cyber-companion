import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { BehaviorDecision } from "./api/behavior";
import {
  requestChatComplete,
  requestChatStream,
  type ChatCompleteResponse,
} from "./api/chat";
import { fetchStoredMessages } from "./api/messages";
import { avatarStates, stateLines, type AvatarState } from "./avatar/types";
import { useAvatarState } from "./avatar/useAvatarState";
import { useBehaviorTicks } from "./avatar/useBehaviorTicks";
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
import { primeAudioPlayback } from "./voice/audioUnlock";
import { usePushToTalk } from "./voice/usePushToTalk";
import { useTextToSpeech } from "./voice/useTextToSpeech";

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
  };
}

function parseAvatarState(value: string): AvatarState {
  if ((avatarStates as readonly string[]).includes(value)) {
    return value as AvatarState;
  }

  return "talking";
}

function App() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [historyStatus, setHistoryStatus] = useState<"loading" | "ready" | "offline">("loading");
  const [isSending, setIsSending] = useState(false);
  const [lastTurn, setLastTurn] = useState<TurnSummary | null>(null);
  const [chatViewCleared, setChatViewCleared] = useState(
    () => sessionStorage.getItem(CHAT_VIEW_CLEARED_KEY) === "1",
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
    cancelScheduledReturn,
    returnToRestState,
    applyRestStateIfResting,
  } = useAvatarState("idle", moodRest.getRestState);
  applyRestStateRef.current = applyRestStateIfResting;
  returnToRestStateRef.current = returnToRestState;
  const messageListRef = useRef<HTMLDivElement>(null);
  const nextMessageIdRef = useRef(1);
  const chatEpochRef = useRef(0);
  const ttsEpochRef = useRef(0);
  const ttsEnabledRef = useRef(false);
  const ttsMutedRef = useRef(false);
  const ttsActiveRef = useRef(false);
  const speakReplyRef = useRef<
    (input: { text: string; decision?: string; avatarState?: string }) => Promise<boolean>
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
    const messageList = messageListRef.current;

    if (!messageList) {
      return;
    }

    messageList.scrollTop = messageList.scrollHeight;
  }, [messages]);

  useEffect(() => {
    const verifyWindow = window as Window & {
      __uiVerify?: {
        refreshMoodRest?: () => Promise<string>;
        returnToRestState?: () => void;
        getAvatarStateLabel?: () => string;
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

            const streamResult = await requestChatStream(userText, {
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
                setMessages((current) =>
                  current.map((message) =>
                    message.id === boxiMessageId
                      ? { ...message, meta: streamMetaToMessageMeta(meta) }
                      : message,
                  ),
                );
              },
              onError: () => {},
            });

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

            const completion = await requestChatComplete(userText);
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

  const handleBehaviorDecision = useCallback(
    async (decision: BehaviorDecision) => {
      const avatar = parseAvatarState(decision.avatar_state);
      const localLine = decision.local_response?.trim() ?? "";

      if (
        localLine &&
        (decision.decision === "mutter" || decision.decision === "proactive")
      ) {
        chatEpochRef.current += 1;
        const messageId = decision.saved_message_id ?? allocateMessageId();
        if (typeof decision.saved_message_id === "number") {
          nextMessageIdRef.current = Math.max(nextMessageIdRef.current, messageId + 1);
        }
        setMessages((current) => [
          ...current,
          {
            id: messageId,
            speaker: "boxi",
            text: localLine,
            meta: { decision: decision.decision },
          },
        ]);
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
    [cancelScheduledReturn, scheduleReturnToIdle, setManualState],
  );

  const { markUserActivity: markBehaviorActivity } = useBehaviorTicks({
    enabled: apiHealth.status === "ok",
    paused: isSending || ttsSpeaking || ttsActiveRef.current,
    onDecision: (decision) => {
      void handleBehaviorDecision(decision);
    },
  });
  markBehaviorActivityRef.current = markBehaviorActivity;

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
          <span className="state-label">{avatarState}</span>
        </div>

        <PixelCharacter state={avatarState} />

        <p className="status-line">{statusText}</p>

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

      <section className="chat-panel" aria-label="Chat">
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

            return (
              <article key={message.id} className={`message ${message.speaker}`}>
                <span className="speaker">{message.speaker === "boxi" ? "Boxi" : "You"}</span>
                <p>{message.text}</p>
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
          {pushToTalkEnabled ? (
            <button
              type="button"
              className={
                pushToTalkState === "recording" ? "ptt-button recording" : "ptt-button"
              }
              aria-pressed={pushToTalkState === "recording"}
              aria-label="Hold to talk"
              disabled={isSending || pushToTalkState === "transcribing"}
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
