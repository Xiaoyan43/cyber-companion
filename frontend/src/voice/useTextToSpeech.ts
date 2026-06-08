import { useCallback, useEffect, useRef, useState } from "react";
import {
  buildTtsStreamUrl,
  evaluateTtsSpeech,
  fetchTtsStatus,
  synthesizeSpeech,
} from "../api/tts";
import { primeAudioPlayback } from "./audioUnlock";
import {
  drainStreamingSpeechChunks,
  flushStreamingSpeechRemainder,
  textForSpeech,
} from "./speechText";

const MUTE_STORAGE_KEY = "cyber-companion-tts-muted";

type SpeakReplyInput = {
  text: string;
  decision?: string;
  avatarState?: string;
};

type StreamingReplyMeta = {
  decision?: string;
  avatarState?: string;
};

type UseTextToSpeechOptions = {
  onSpeakingStart?: () => void;
  onSpeakingEnd?: () => void;
  onError?: (message: string) => void;
};

type StreamingSession = {
  active: boolean;
  rawBuffer: string;
  accumulatedRaw: string;
  sessionId: number;
  streamFinished: boolean;
  speakApproved: boolean | null;
  decision?: string;
  avatarState?: string;
  startedSpeaking: boolean;
  queue: string[];
};

function createStreamingSession(sessionId: number): StreamingSession {
  return {
    active: true,
    rawBuffer: "",
    accumulatedRaw: "",
    sessionId,
    streamFinished: false,
    speakApproved: null,
    decision: undefined,
    avatarState: undefined,
    startedSpeaking: false,
    queue: [],
  };
}

function waitForQueueProcessor(
  sessionId: number,
  sessionRef: React.MutableRefObject<number>,
  processingRef: React.MutableRefObject<boolean>,
): Promise<void> {
  return new Promise((resolve) => {
    const poll = () => {
      if (sessionId !== sessionRef.current || !processingRef.current) {
        resolve();
        return;
      }

      window.setTimeout(poll, 16);
    };

    poll();
  });
}

function readMutedPreference(): boolean {
  try {
    return window.localStorage.getItem(MUTE_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function writeMutedPreference(muted: boolean) {
  try {
    window.localStorage.setItem(MUTE_STORAGE_KEY, muted ? "1" : "0");
  } catch {
    // Ignore storage failures in restricted environments.
  }
}

function playAudioClip(
  mimeType: string,
  audioBase64: string,
  audioRef: React.MutableRefObject<HTMLAudioElement | null>,
  sessionId: number,
  sessionRef: React.MutableRefObject<number>,
): Promise<boolean> {
  if (sessionId !== sessionRef.current) {
    return Promise.resolve(false);
  }

  return new Promise((resolve) => {
    primeAudioPlayback();
    const audio = new Audio(`data:${mimeType};base64,${audioBase64}`);
    audio.volume = 1;
    audioRef.current = audio;

    const finish = (played: boolean) => {
      if (audioRef.current === audio) {
        audioRef.current = null;
      }
      resolve(played && sessionId === sessionRef.current);
    };

    audio.addEventListener("ended", () => finish(true), { once: true });
    audio.addEventListener("error", () => finish(false), { once: true });
    void audio.play().catch(() => finish(false));
  });
}

function playStreamingAudio(
  streamUrl: string,
  audioRef: React.MutableRefObject<HTMLAudioElement | null>,
  sessionId: number,
  sessionRef: React.MutableRefObject<number>,
  signal?: AbortSignal,
): Promise<boolean> {
  if (sessionId !== sessionRef.current) {
    return Promise.resolve(false);
  }

  return new Promise((resolve) => {
    primeAudioPlayback();
    const audio = new Audio(streamUrl);
    audio.preload = "auto";
    audio.volume = 1;
    audioRef.current = audio;

    let settled = false;
    const finish = (played: boolean) => {
      if (settled) {
        return;
      }
      settled = true;
      signal?.removeEventListener("abort", onAbort);
      if (audioRef.current === audio) {
        audioRef.current = null;
      }
      resolve(played && sessionId === sessionRef.current);
    };

    const onAbort = () => {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      finish(false);
    };

    const attemptPlay = () => {
      void audio.play().catch(() => finish(false));
    };

    signal?.addEventListener("abort", onAbort, { once: true });
    audio.addEventListener("ended", () => finish(true), { once: true });
    audio.addEventListener("error", () => finish(false), { once: true });
    audio.addEventListener("canplay", attemptPlay, { once: true });
    attemptPlay();
  });
}

export function useTextToSpeech({
  onSpeakingStart,
  onSpeakingEnd,
  onError,
}: UseTextToSpeechOptions) {
  const [enabled, setEnabled] = useState(false);
  const [muted, setMuted] = useState(readMutedPreference);
  const [speaking, setSpeaking] = useState(false);
  const [providerName, setProviderName] = useState<string | null>(null);
  const [forceMock, setForceMock] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const speakingRef = useRef(false);
  const ttsInFlightRef = useRef(false);
  const streamAbortRef = useRef<AbortController | null>(null);
  const playbackSessionRef = useRef(0);
  const maxSpeechCharsRef = useRef(120);
  const streamingRef = useRef<StreamingSession | null>(null);
  const queueProcessingRef = useRef(false);
  const onSpeakingStartRef = useRef(onSpeakingStart);
  const onSpeakingEndRef = useRef(onSpeakingEnd);
  const onErrorRef = useRef(onError);
  const enabledRef = useRef(enabled);
  const mutedRef = useRef(muted);

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  useEffect(() => {
    mutedRef.current = muted;
  }, [muted]);

  useEffect(() => {
    onSpeakingStartRef.current = onSpeakingStart;
    onSpeakingEndRef.current = onSpeakingEnd;
    onErrorRef.current = onError;
  });

  useEffect(() => {
    const unlockAudio = () => primeAudioPlayback();

    window.addEventListener("pointerdown", unlockAudio);
    window.addEventListener("keydown", unlockAudio);

    return () => {
      window.removeEventListener("pointerdown", unlockAudio);
      window.removeEventListener("keydown", unlockAudio);
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadStatus() {
      try {
        const status = await fetchTtsStatus();
        if (!active) {
          return;
        }

        setEnabled(status.enabled);
        setProviderName(status.default_provider);
        setForceMock(status.force_mock);
        maxSpeechCharsRef.current = status.max_speech_chars;
      } catch {
        if (!active) {
          return;
        }

        setEnabled(false);
      }
    }

    void loadStatus();

    return () => {
      active = false;
    };
  }, []);

  const clearCurrentAudio = useCallback(() => {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;

    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      audioRef.current = null;
    }
  }, []);

  const resetStreamingSession = useCallback(() => {
    streamingRef.current = null;
    queueProcessingRef.current = false;
  }, []);

  const invalidatePlayback = useCallback(() => {
    playbackSessionRef.current += 1;
    clearCurrentAudio();
    resetStreamingSession();
    speakingRef.current = false;
    setSpeaking(false);
    ttsInFlightRef.current = false;
  }, [clearCurrentAudio, resetStreamingSession]);

  const stopSpeaking = useCallback(
    (notifyEnd = false) => {
      const wasSpeaking = speakingRef.current;
      invalidatePlayback();

      if (notifyEnd && wasSpeaking) {
        onSpeakingEndRef.current?.();
      }
    },
    [invalidatePlayback],
  );

  useEffect(
    () => () => {
      playbackSessionRef.current += 1;
      streamAbortRef.current?.abort();
      streamAbortRef.current = null;
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audio.removeAttribute("src");
        audio.load();
        audioRef.current = null;
      }
      speakingRef.current = false;
      streamingRef.current = null;
    },
    [],
  );

  const toggleMuted = useCallback(() => {
    primeAudioPlayback();
    setMuted((current) => {
      const next = !current;
      writeMutedPreference(next);
      if (next) {
        stopSpeaking(true);
      }
      return next;
    });
  }, [stopSpeaking]);

  const playBufferedFallback = useCallback(
    async (
      speechText: string,
      decision: string | undefined,
      avatarState: string | undefined,
      sessionId: number,
    ): Promise<boolean> => {
      const result = await synthesizeSpeech({
        text: speechText,
        decision,
        avatarState,
      });

      if (!enabledRef.current || mutedRef.current || sessionId !== playbackSessionRef.current) {
        return false;
      }

      if (!result.spoken || !result.audio_base64 || !result.mime_type) {
        const message = result.spoken
          ? "TTS returned no audio."
          : `TTS skipped: ${result.reason}`;
        setLastError(message);
        onErrorRef.current?.(message);
        return false;
      }

      return playAudioClip(
        result.mime_type,
        result.audio_base64,
        audioRef,
        sessionId,
        playbackSessionRef,
      );
    },
    [],
  );

  const maybeFinishStreamingSpeaking = useCallback((sessionId: number) => {
    const streaming = streamingRef.current;
    if (
      !streaming ||
      streaming.sessionId !== sessionId ||
      sessionId !== playbackSessionRef.current ||
      !streaming.streamFinished ||
      streaming.queue.length > 0 ||
      queueProcessingRef.current ||
      !streaming.startedSpeaking
    ) {
      return;
    }

    streaming.active = false;
    speakingRef.current = false;
    setSpeaking(false);
    onSpeakingEndRef.current?.();
  }, []);

  const ensureSpeakApproved = useCallback(
    async (streaming: StreamingSession): Promise<boolean> => {
      if (streaming.speakApproved !== null) {
        return streaming.speakApproved;
      }

      const speechText = textForSpeech(streaming.accumulatedRaw, maxSpeechCharsRef.current);
      if (!speechText) {
        streaming.speakApproved = false;
        return false;
      }

      try {
        const evaluation = await evaluateTtsSpeech({
          text: speechText,
          decision: streaming.decision,
          avatarState: streaming.avatarState,
        });
        streaming.speakApproved = evaluation.should_speak;
      } catch {
        if (
          streaming.sessionId !== playbackSessionRef.current ||
          !enabledRef.current ||
          mutedRef.current
        ) {
          streaming.speakApproved = false;
          return false;
        }
        streaming.speakApproved = true;
      }

      return streaming.speakApproved;
    },
    [],
  );

  const processStreamingQueue = useCallback(
    async (sessionId: number) => {
      if (queueProcessingRef.current) {
        return;
      }

      queueProcessingRef.current = true;

      try {
        while (sessionId === playbackSessionRef.current) {
          const streaming = streamingRef.current;
          if (!streaming || streaming.sessionId !== sessionId || !streaming.active) {
            break;
          }

          if (!enabledRef.current || mutedRef.current) {
            streaming.queue = [];
            break;
          }

          if (streaming.speakApproved === false) {
            streaming.queue = [];
            break;
          }

          const nextSentence = streaming.queue.shift();
          if (!nextSentence) {
            break;
          }

          if (streaming.speakApproved === null) {
            const approved = await ensureSpeakApproved(streaming);
            if (!approved || sessionId !== playbackSessionRef.current) {
              streaming.queue = [];
              break;
            }
          }

          const abortController = new AbortController();
          streamAbortRef.current = abortController;

          if (!streaming.startedSpeaking) {
            streaming.startedSpeaking = true;
            onSpeakingStartRef.current?.();
            speakingRef.current = true;
            setSpeaking(true);
          }

          const streamUrl = buildTtsStreamUrl({
            text: nextSentence,
            decision: streaming.decision,
            avatarState: streaming.avatarState,
          });
          const playbackUrl = `${streamUrl}&_play=${sessionId}`;

          let played = await playStreamingAudio(
            playbackUrl,
            audioRef,
            sessionId,
            playbackSessionRef,
            abortController.signal,
          );

          if (
            !played &&
            enabledRef.current &&
            !mutedRef.current &&
            sessionId === playbackSessionRef.current
          ) {
            clearCurrentAudio();
            played = await playBufferedFallback(
              nextSentence,
              streaming.decision,
              streaming.avatarState,
              sessionId,
            );
          }

          if (streamAbortRef.current === abortController) {
            streamAbortRef.current = null;
          }

          if (sessionId !== playbackSessionRef.current) {
            break;
          }
        }
      } finally {
        queueProcessingRef.current = false;
        maybeFinishStreamingSpeaking(sessionId);
      }
    },
    [clearCurrentAudio, ensureSpeakApproved, maybeFinishStreamingSpeaking, playBufferedFallback],
  );

  const enqueueStreamingChunks = useCallback(
    (sessionId: number) => {
      const streaming = streamingRef.current;
      if (!streaming || streaming.sessionId !== sessionId || !streaming.active) {
        return;
      }

      const { chunks, remainder } = drainStreamingSpeechChunks(
        streaming.rawBuffer,
        maxSpeechCharsRef.current,
      );
      streaming.rawBuffer = remainder;

      if (chunks.length > 0) {
        streaming.queue.push(...chunks);
        void processStreamingQueue(sessionId);
      }
    },
    [processStreamingQueue],
  );

  const cancelStreamingReply = useCallback(() => {
    invalidatePlayback();
  }, [invalidatePlayback]);

  const beginStreamingReply = useCallback(() => {
    if (!enabledRef.current || mutedRef.current) {
      return false;
    }

    playbackSessionRef.current += 1;
    const sessionId = playbackSessionRef.current;
    clearCurrentAudio();
    streamingRef.current = createStreamingSession(sessionId);
    ttsInFlightRef.current = true;
    setLastError(null);
    return true;
  }, [clearCurrentAudio]);

  const feedStreamingReplyDelta = useCallback(
    (delta: string) => {
      const streaming = streamingRef.current;
      if (!streaming?.active || !delta) {
        return;
      }

      if (!enabledRef.current || mutedRef.current) {
        return;
      }

      streaming.rawBuffer += delta;
      streaming.accumulatedRaw += delta;
      enqueueStreamingChunks(streaming.sessionId);
    },
    [enqueueStreamingChunks],
  );

  const finishStreamingReply = useCallback(
    async ({ decision, avatarState }: StreamingReplyMeta = {}): Promise<boolean> => {
      const streaming = streamingRef.current;
      if (!streaming?.active) {
        ttsInFlightRef.current = false;
        return false;
      }

      const sessionId = streaming.sessionId;
      streaming.decision = decision;
      streaming.avatarState = avatarState;
      streaming.streamFinished = true;

      const tailChunks = flushStreamingSpeechRemainder(
        streaming.rawBuffer,
        maxSpeechCharsRef.current,
      );
      streaming.rawBuffer = "";
      if (tailChunks.length > 0) {
        streaming.queue.push(...tailChunks);
      }

      if (
        streaming.speakApproved === null &&
        streaming.queue.length > 0 &&
        enabledRef.current &&
        !mutedRef.current &&
        sessionId === playbackSessionRef.current
      ) {
        const approved = await ensureSpeakApproved(streaming);
        if (!approved) {
          streaming.queue = [];
          clearCurrentAudio();
          streaming.active = false;
          ttsInFlightRef.current = false;
          return false;
        }
      }

      while (
        streaming.queue.length > 0 &&
        sessionId === playbackSessionRef.current &&
        streamingRef.current?.sessionId === sessionId
      ) {
        await processStreamingQueue(sessionId);
        await waitForQueueProcessor(sessionId, playbackSessionRef, queueProcessingRef);
      }

      maybeFinishStreamingSpeaking(sessionId);

      const spoke = streaming.startedSpeaking && sessionId === playbackSessionRef.current;
      if (streaming.sessionId === sessionId) {
        streaming.active = false;
      }
      ttsInFlightRef.current = false;
      return spoke;
    },
    [
      clearCurrentAudio,
      ensureSpeakApproved,
      maybeFinishStreamingSpeaking,
      processStreamingQueue,
    ],
  );

  const speakReply = useCallback(
    async ({ text, decision, avatarState }: SpeakReplyInput) => {
      const speechText = textForSpeech(text, maxSpeechCharsRef.current);
      if (!enabledRef.current || mutedRef.current || !speechText) {
        return false;
      }

      if (speakingRef.current || ttsInFlightRef.current) {
        return false;
      }

      ttsInFlightRef.current = true;
      setLastError(null);

      playbackSessionRef.current += 1;
      const sessionId = playbackSessionRef.current;
      const abortController = new AbortController();
      streamAbortRef.current = abortController;
      resetStreamingSession();

      try {
        clearCurrentAudio();

        try {
          const evaluation = await evaluateTtsSpeech({
            text: speechText,
            decision,
            avatarState,
          });
          if (!evaluation.should_speak) {
            return false;
          }
        } catch {
          if (abortController.signal.aborted || sessionId !== playbackSessionRef.current) {
            return false;
          }
          // Evaluate is best-effort; still attempt playback if the check fails.
        }

        if (!enabledRef.current || mutedRef.current || sessionId !== playbackSessionRef.current) {
          return false;
        }

        const streamUrl = buildTtsStreamUrl({
          text: speechText,
          decision,
          avatarState,
        });
        const playbackUrl = `${streamUrl}&_play=${sessionId}`;

        onSpeakingStartRef.current?.();
        speakingRef.current = true;
        setSpeaking(true);

        let played = await playStreamingAudio(
          playbackUrl,
          audioRef,
          sessionId,
          playbackSessionRef,
          abortController.signal,
        );

        if (
          !played &&
          enabledRef.current &&
          !mutedRef.current &&
          sessionId === playbackSessionRef.current
        ) {
          clearCurrentAudio();
          played = await playBufferedFallback(speechText, decision, avatarState, sessionId);
        }

        if (sessionId === playbackSessionRef.current) {
          speakingRef.current = false;
          setSpeaking(false);
          onSpeakingEndRef.current?.();
        }

        return played;
      } catch (error) {
        const message = error instanceof Error ? error.message : "TTS playback failed.";
        setLastError(message);
        onErrorRef.current?.(message);
        if (sessionId === playbackSessionRef.current) {
          speakingRef.current = false;
          setSpeaking(false);
        }
        return false;
      } finally {
        if (streamAbortRef.current === abortController) {
          streamAbortRef.current = null;
        }
        ttsInFlightRef.current = false;
      }
    },
    [clearCurrentAudio, playBufferedFallback, resetStreamingSession],
  );

  return {
    enabled,
    muted,
    speaking,
    providerName,
    forceMock,
    lastError,
    toggleMuted,
    speakReply,
    beginStreamingReply,
    feedStreamingReplyDelta,
    finishStreamingReply,
    cancelStreamingReply,
    stopSpeaking,
  };
}
