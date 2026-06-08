import { useCallback, useEffect, useRef, useState } from "react";
import {
  buildTtsStreamUrl,
  evaluateTtsSpeech,
  fetchTtsStatus,
  synthesizeSpeech,
} from "../api/tts";
import { primeAudioPlayback } from "./audioUnlock";
import { textForSpeech } from "./speechText";

const MUTE_STORAGE_KEY = "cyber-companion-tts-muted";

type SpeakReplyInput = {
  text: string;
  decision?: string;
  avatarState?: string;
};

type UseTextToSpeechOptions = {
  onSpeakingStart?: () => void;
  onSpeakingEnd?: () => void;
  onError?: (message: string) => void;
};

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

  const stopSpeaking = useCallback((notifyEnd = false) => {
    playbackSessionRef.current += 1;
    const wasSpeaking = speakingRef.current;
    clearCurrentAudio();

    speakingRef.current = false;
    setSpeaking(false);
    ttsInFlightRef.current = false;

    if (notifyEnd && wasSpeaking) {
      onSpeakingEndRef.current?.();
    }
  }, [clearCurrentAudio]);

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
      ttsInFlightRef.current = false;
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

  const speakReply = useCallback(
    async ({ text, decision, avatarState }: SpeakReplyInput) => {
      const speechText = textForSpeech(text, maxSpeechCharsRef.current);
      if (!enabledRef.current || mutedRef.current || !speechText) {
        return false;
      }

      ttsInFlightRef.current = true;
      setLastError(null);

      playbackSessionRef.current += 1;
      const sessionId = playbackSessionRef.current;
      const abortController = new AbortController();
      streamAbortRef.current = abortController;

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
    [clearCurrentAudio, playBufferedFallback],
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
    stopSpeaking,
  };
}
