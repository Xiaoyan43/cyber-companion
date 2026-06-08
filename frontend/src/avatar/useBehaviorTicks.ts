import { useEffect, useRef } from "react";
import { evaluateBehavior, type BehaviorDecision } from "../api/behavior";

const IDLE_TICK_MS = 90_000;
const PROACTIVE_CHECK_MS = 300_000;
const USER_QUIET_MS = 120_000;

type UseBehaviorTicksOptions = {
  enabled: boolean;
  paused: boolean;
  onDecision: (decision: BehaviorDecision) => void;
  onError?: (message: string) => void;
};

export function useBehaviorTicks({
  enabled,
  paused,
  onDecision,
  onError,
}: UseBehaviorTicksOptions) {
  const lastUserActivityRef = useRef(Date.now());
  const onDecisionRef = useRef(onDecision);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onDecisionRef.current = onDecision;
  }, [onDecision]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    if (!enabled || paused) {
      return;
    }

    let cancelled = false;

    async function runIdleTick() {
      if (cancelled || document.visibilityState === "hidden") {
        return;
      }

      try {
        const decision = await evaluateBehavior("idle_tick");
        if (!cancelled) {
          onDecisionRef.current(decision);
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "idle tick failed";
          onErrorRef.current?.(message);
        }
      }
    }

    async function runProactiveCheck() {
      if (cancelled || document.visibilityState === "hidden") {
        return;
      }

      if (Date.now() - lastUserActivityRef.current < USER_QUIET_MS) {
        return;
      }

      try {
        const decision = await evaluateBehavior("proactive_check");
        if (!cancelled) {
          onDecisionRef.current(decision);
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "proactive check failed";
          onErrorRef.current?.(message);
        }
      }
    }

    const idleTimer = window.setInterval(() => {
      void runIdleTick();
    }, IDLE_TICK_MS);

    const proactiveTimer = window.setInterval(() => {
      void runProactiveCheck();
    }, PROACTIVE_CHECK_MS);

    return () => {
      cancelled = true;
      window.clearInterval(idleTimer);
      window.clearInterval(proactiveTimer);
    };
  }, [enabled, paused]);

  const markUserActivity = () => {
    lastUserActivityRef.current = Date.now();
  };

  return { markUserActivity };
}
