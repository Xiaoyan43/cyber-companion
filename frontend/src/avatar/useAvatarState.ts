import { useCallback, useEffect, useRef, useState } from "react";
import { isRestAvatarState } from "./restMood";
import type { AvatarState } from "./types";
import { avatarStateDuration, avatarTiming } from "./timing";

export type ChatFetchResult = {
  replyText: string;
  avatarState?: AvatarState;
  meta?: Record<string, unknown>;
  streamed?: boolean;
  translation?: string | null;
};

export type ChatReplyHandoff = {
  deferIdleFallback?: boolean;
};

type GetRestState = () => AvatarState;

export function useAvatarState(
  initialState: AvatarState = "idle",
  getRestState?: GetRestState,
) {
  const [avatarState, setAvatarState] = useState<AvatarState>(initialState);
  const timersRef = useRef<number[]>([]);
  const getRestStateRef = useRef(getRestState);

  useEffect(() => {
    getRestStateRef.current = getRestState;
  }, [getRestState]);

  const resolveRestState = useCallback((): AvatarState => {
    return getRestStateRef.current?.() ?? "idle";
  }, []);

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

  const returnToRestState = useCallback(() => {
    clearTimers();
    setAvatarState(resolveRestState());
  }, [clearTimers, resolveRestState]);

  const applyRestStateIfResting = useCallback(
    (nextRest?: AvatarState) => {
      setAvatarState((current) => {
        if (!isRestAvatarState(current)) {
          return current;
        }

        return nextRest ?? resolveRestState();
      });
    },
    [resolveRestState],
  );

  const scheduleReturnToIdle = useCallback(
    (state: AvatarState, replyText: string) => {
      clearTimers();
      setAvatarState(state);
      schedule(() => setAvatarState(resolveRestState()), avatarStateDuration(state, replyText));
    },
    [clearTimers, resolveRestState, schedule],
  );

  const scheduleReturnForMs = useCallback(
    (state: AvatarState, holdMs: number) => {
      clearTimers();
      setAvatarState(state);
      schedule(() => setAvatarState(resolveRestState()), holdMs);
    },
    [clearTimers, resolveRestState, schedule],
  );

  const runEmptySubmitSequence = useCallback(() => {
    clearTimers();
    setAvatarState("annoyed");
    schedule(() => setAvatarState(resolveRestState()), avatarTiming.annoyedMs);
  }, [clearTimers, resolveRestState, schedule]);

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
          () => setAvatarState(resolveRestState()),
          avatarStateDuration(activeState, result.replyText),
        );
      } catch (error) {
        setAvatarState("annoyed");
        schedule(() => setAvatarState(resolveRestState()), avatarTiming.annoyedMs);
        throw error;
      }
    },
    [clearTimers, resolveRestState, schedule],
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
    scheduleReturnForMs,
    cancelScheduledReturn,
    returnToRestState,
    applyRestStateIfResting,
  };
}
