import { useCallback, useEffect, useRef, useState } from "react";
import type { AvatarState } from "./types";
import { avatarStateDuration, avatarTiming, talkingDuration } from "./timing";

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

  const runChatReplySequence = useCallback(
    (replyText: string, onTalkingStart?: () => void) => {
      clearTimers();
      setAvatarState("thinking");

      schedule(() => {
        onTalkingStart?.();
        setAvatarState("talking");
        schedule(() => setAvatarState("idle"), talkingDuration(replyText));
      }, avatarTiming.thinkingMs);
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
      fetchReply: () => Promise<{
        replyText: string;
        avatarState?: AvatarState;
        meta?: Record<string, unknown>;
      }>,
      onReplyReady?: (result: {
        replyText: string;
        avatarState?: AvatarState;
        meta?: Record<string, unknown>;
      }) => void | Promise<void>,
    ) => {
      clearTimers();
      setAvatarState("thinking");

      try {
        const result = await fetchReply();
        await onReplyReady?.(result);
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
    runChatReplySequence,
    runChatFetchSequence,
    runEmptySubmitSequence,
    cancelScheduledReturn,
  };
}
