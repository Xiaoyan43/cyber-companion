import { useCallback, useEffect, useState } from "react";
import { fetchPipecatStatus, startPipecat, stopPipecat } from "./pipecatApi";
import { useVoiceTranscript } from "./useVoiceTranscript";

export type PipecatVoicePhase =
  | "checking"
  | "stopped"
  | "starting"
  | "running"
  | "stopping"
  | "error";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const STATUS_POLL_MS = 1500;

export function usePipecatVoice() {
  const [phase, setPhase] = useState<PipecatVoicePhase>("checking");
  const [error, setError] = useState<string | null>(null);
  const isRunning = phase === "running";
  const transcript = useVoiceTranscript(isRunning, apiBaseUrl);

  const refreshStatus = useCallback(async () => {
    try {
      const status = await fetchPipecatStatus();
      if (status.status === "running") {
        setError(null);
        setPhase("running");
        return;
      }
      if (status.last_error) {
        setError(status.last_error);
        setPhase("error");
        return;
      }
      setError(null);
      setPhase("stopped");
    } catch (statusError: unknown) {
      setError(statusError instanceof Error ? statusError.message : "Soul voice unavailable");
      setPhase("error");
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  useEffect(() => {
    if (!isRunning) {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshStatus();
    }, STATUS_POLL_MS);
    return () => window.clearInterval(timer);
  }, [isRunning, refreshStatus]);

  const start = useCallback(async () => {
    setError(null);
    setPhase("starting");
    try {
      await startPipecat();
      await refreshStatus();
    } catch (startError: unknown) {
      setError(startError instanceof Error ? startError.message : "Soul voice failed to start");
      setPhase("error");
    }
  }, [refreshStatus]);

  const stop = useCallback(async () => {
    setError(null);
    setPhase("stopping");
    try {
      await stopPipecat();
      setPhase("stopped");
    } catch (stopError: unknown) {
      setError(stopError instanceof Error ? stopError.message : "Soul voice failed to stop");
      setPhase("error");
    }
  }, []);

  return {
    phase,
    error,
    isRunning,
    transcript,
    start,
    stop,
    refreshStatus,
  };
}
