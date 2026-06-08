import { useCallback, useEffect, useRef } from "react";
import { fetchMoodState } from "../api/mood";
import type { AvatarState } from "./types";
import { MOOD_POLL_MS, moodToRestState } from "./restMood";

type UseMoodRestOptions = {
  enabled: boolean;
  onMoodRestUpdated?: (restState: AvatarState) => void;
};

export function useMoodRest({ enabled, onMoodRestUpdated }: UseMoodRestOptions) {
  const restStateRef = useRef<AvatarState>("idle");
  const onUpdateRef = useRef(onMoodRestUpdated);

  useEffect(() => {
    onUpdateRef.current = onMoodRestUpdated;
  }, [onMoodRestUpdated]);

  const refreshMood = useCallback(async () => {
    if (!enabled || document.visibilityState === "hidden") {
      return restStateRef.current;
    }

    try {
      const mood = await fetchMoodState();
      const restState = moodToRestState(mood);
      restStateRef.current = restState;
      onUpdateRef.current?.(restState);
      return restState;
    } catch {
      return restStateRef.current;
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let cancelled = false;

    const poll = async () => {
      if (cancelled) {
        return;
      }

      await refreshMood();
    };

    void poll();

    const intervalId = window.setInterval(() => {
      void poll();
    }, MOOD_POLL_MS);

    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        void poll();
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [enabled, refreshMood]);

  const getRestState = useCallback(() => restStateRef.current, []);

  return {
    getRestState,
    refreshMood,
  };
}
