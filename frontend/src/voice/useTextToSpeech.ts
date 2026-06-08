import { useCallback, useEffect, useRef, useState } from "react";
import { fetchTtsStatus, synthesizeSpeech } from "../api/tts";
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
  const maxSpeechCharsRef = useRef(120);
  const onSpeakingStartRef = useRef(onSpeakingStart);
  const onSpeakingEndRef = useRef(onSpeakingEnd);
  const onErrorRef = useRef(onError);

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

  const stopSpeaking = useCallback((notifyEnd = false) => {
    const wasSpeaking = speakingRef.current;
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
      audioRef.current = null;
    }

    speakingRef.current = false;
    setSpeaking(false);

    if (notifyEnd && wasSpeaking) {
      onSpeakingEndRef.current?.();
    }
  }, []);

  useEffect(
    () => () => {
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audioRef.current = null;
      }
      speakingRef.current = false;
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

  const speakReply = useCallback(
    async ({ text, decision, avatarState }: SpeakReplyInput) => {
      const speechText = textForSpeech(text, maxSpeechCharsRef.current);
      if (!enabled || muted || !speechText || speakingRef.current) {
        return false;
      }

      setLastError(null);

      try {
        const result = await synthesizeSpeech({
          text: speechText,
          decision,
          avatarState,
        });

        if (!result.spoken || !result.audio_base64 || !result.mime_type) {
          const message = result.spoken
            ? "TTS returned no audio."
            : `TTS skipped: ${result.reason}`;
          setLastError(message);
          onErrorRef.current?.(message);
          return false;
        }

        if (audioRef.current) {
          stopSpeaking();
        }

        onSpeakingStartRef.current?.();
        speakingRef.current = true;
        setSpeaking(true);

        primeAudioPlayback();
        const audio = new Audio(`data:${result.mime_type};base64,${result.audio_base64}`);
        audio.volume = 1;
        audioRef.current = audio;

        const finish = (notifyEnd: boolean) => {
          if (audioRef.current === audio) {
            audioRef.current = null;
          }
          speakingRef.current = false;
          setSpeaking(false);
          if (notifyEnd) {
            onSpeakingEndRef.current?.();
          }
        };

        audio.addEventListener("ended", () => finish(true), { once: true });
        audio.addEventListener("error", () => finish(true), { once: true });

        try {
          await audio.play();
        } catch (error) {
          finish(false);
          const message = error instanceof Error ? error.message : "TTS playback failed.";
          setLastError(message);
          onErrorRef.current?.(message);
          return false;
        }

        return true;
      } catch (error) {
        const message = error instanceof Error ? error.message : "TTS playback failed.";
        setLastError(message);
        onErrorRef.current?.(message);
        speakingRef.current = false;
        setSpeaking(false);
        return false;
      }
    },
    [enabled, muted, stopSpeaking],
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
