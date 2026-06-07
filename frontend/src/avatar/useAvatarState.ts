import { useCallback, useEffect, useRef, useState } from "react";
import type { AvatarState } from "./types";
import { avatarStateDuration, avatarTiming } from "./timing";

export type ChatFetchResult = {
  replyText: string;
  avatarState?: AvatarState;
  meta?: Record<string, unknown>;
};

export type ChatReplyHandoff = {
  deferIdleFallback?: boolean;
};

export function useAvatarState(initialState: AvatarState = "idle") {
  const [avatarState, setAvatarState] = useState<AvatarState>(initialState);
  const timersRef = useRef<number[]>([]);

  const clearTimers = useCallback(() => {
    for (const timerId of timersRef.current) {
      window.clearTimeout(timerId);
    }

    timersRef.current = [];
  }, []);

  const schedule = useCallback((callback: () => void, delayMs: number) => {
    const timerId = window.setTimeout(callback, delayMs);
    timersRef.current.push(timerId);
  }, []);

  const setManualState = useCallback(
    (state: AvatarState) => {
      clearTimers();
      setAvatarState(state);
    },
    [clearTimers],
  );

  const scheduleReturnToIdle = useCallback(
    (state: AvatarState, replyText: string) => {
      clearTimers();
      setAvatarState(state);
      schedule(() => setAvatarState("idle"), avatarStateDuration(state, replyText));
    },
    [clearTimers, schedule],
  );

  const runEmptySubmitSequence = useCallback(() => {
    clearTimers();
    setAvatarState("annoyed");
    schedule(() => setAvatarState("idle"), avatarTiming.annoyedMs);
  }, [clearTimers, schedule]);

  const runChatFetchSequence = useCallback(
    async (
      fetchReply: () => Promise<ChatFetchResult>,
      onReplyReady?: (result: ChatFetchResult) => void | Promise<void | ChatReplyHandoff>,
    ) => {
      clearTimers();
      setAvatarState("thinking");

      try {
        const result = await fetchReply();
        const handoff = await onReplyReady?.(result);
        if (handoff?.deferIdleFallback) {
          return;
        }
        const activeState = result.avatarState ?? "talking";
        setAvatarState(activeState);
        schedule(
          () => setAvatarState("idle"),
          avatarStateDuration(activeState, result.replyText),
        );
      } catch (error) {
        setAvatarState("annoyed");
        schedule(() => setAvatarState("idle"), avatarTiming.annoyedMs);
        throw error;
      }
    },
    [clearTimers, schedule],
  );

  const cancelScheduledReturn = useCallback(() => {
    clearTimers();
  }, [clearTimers]);

  useEffect(() => clearTimers, [clearTimers]);

  return {
    avatarState,
    setManualState,
    runChatFetchSequence,
    runEmptySubmitSequence,
    scheduleReturnToIdle,
    cancelScheduledReturn,
  };
}
