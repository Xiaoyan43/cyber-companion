import { useCallback, useEffect, useRef, useState } from "react";
import { fetchTtsStatus, synthesizeSpeech } from "../api/tts";

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
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const speakingRef = useRef(false);
  const audioUnlockedRef = useRef(false);

  useEffect(() => {
    const unlockAudio = () => {
      if (audioUnlockedRef.current) {
        return;
      }

      const silent = new Audio(
        "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==",
      );
      void silent.play().then(() => {
        audioUnlockedRef.current = true;
        silent.pause();
        silent.currentTime = 0;
      }).catch(() => {
        // Browser may still allow later playback after an explicit user gesture.
      });
    };

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

  const stopSpeaking = useCallback(
    (notifyEnd = false) => {
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
        onSpeakingEnd?.();
      }
    },
    [onSpeakingEnd],
  );

  useEffect(() => () => stopSpeaking(), [stopSpeaking]);

  const toggleMuted = useCallback(() => {
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
      const trimmed = text.trim();
      if (!enabled || muted || !trimmed || speaking) {
        return false;
      }

      try {
        const result = await synthesizeSpeech({
          text: trimmed,
          decision,
          avatarState,
        });

        if (!result.spoken || !result.audio_base64 || !result.mime_type) {
          return false;
        }

        stopSpeaking();
        onSpeakingStart?.();
        speakingRef.current = true;
        setSpeaking(true);

        const audio = new Audio(`data:${result.mime_type};base64,${result.audio_base64}`);
        audioRef.current = audio;

        const finish = () => {
          if (audioRef.current === audio) {
            audioRef.current = null;
          }
          speakingRef.current = false;
          setSpeaking(false);
          onSpeakingEnd?.();
        };

        audio.addEventListener("ended", finish, { once: true });
        audio.addEventListener("error", finish, { once: true });

        try {
          await audio.play();
        } catch (error) {
          finish();
          const message = error instanceof Error ? error.message : "TTS playback failed.";
          onError?.(message);
          return false;
        }

        return true;
      } catch (error) {
        const message = error instanceof Error ? error.message : "TTS playback failed.";
        onError?.(message);
        speakingRef.current = false;
        setSpeaking(false);
        return false;
      }
    },
    [enabled, muted, onError, onSpeakingEnd, onSpeakingStart, speaking, stopSpeaking],
  );

  return {
    enabled,
    muted,
    speaking,
    toggleMuted,
    speakReply,
    stopSpeaking,
  };
}
