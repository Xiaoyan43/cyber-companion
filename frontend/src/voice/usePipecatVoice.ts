import { useCallback, useEffect, useState } from "react";
import { fetchPipecatStatus, stopPipecat } from "./pipecatApi";
import { useVoiceTranscript } from "./useVoiceTranscript";
import { useWebRtcVoiceConnection } from "./useWebRtcVoiceConnection";

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
  const { connect, disconnect } = useWebRtcVoiceConnection();

  const refreshStatus = useCallback(async () => {
    try {
      const status = await fetchPipecatStatus();
      if (status.status === "running") {
        setError(null);
        setPhase("running");
        return;
      }
      // Backend is not running (stopped/errored, possibly without us calling
      // stop() ourselves, e.g. a pipeline crash) — release the local mic/pc.
      disconnect();
      if (status.last_error) {
        setError(status.last_error);
        setPhase("error");
        return;
      }
      setError(null);
      setPhase("stopped");
    } catch (statusError: unknown) {
      disconnect();
      setError(statusError instanceof Error ? statusError.message : "Soul voice unavailable");
      setPhase("error");
    }
  }, [disconnect]);

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
      await connect();
      await refreshStatus();
    } catch (startError: unknown) {
      disconnect();
      setError(startError instanceof Error ? startError.message : "Soul voice failed to start");
      setPhase("error");
    }
  }, [connect, disconnect, refreshStatus]);

  const stop = useCallback(async () => {
    setError(null);
    setPhase("stopping");
    disconnect();
    try {
      await stopPipecat();
      setPhase("stopped");
    } catch (stopError: unknown) {
      setError(stopError instanceof Error ? stopError.message : "Soul voice failed to stop");
      setPhase("error");
    }
  }, [disconnect]);

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
