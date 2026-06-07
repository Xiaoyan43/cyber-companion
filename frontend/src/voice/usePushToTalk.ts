import { useCallback, useEffect, useRef, useState, type MouseEvent, type PointerEvent } from "react";
import { fetchSttStatus, transcribeAudio } from "../api/stt";

export type PushToTalkState = "idle" | "recording" | "transcribing" | "error";

type UsePushToTalkOptions = {
  onTranscript: (text: string) => void | Promise<void>;
  onError?: (message: string) => void;
};

function pickMimeType(): string | undefined {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];

  if (typeof MediaRecorder === "undefined" || typeof MediaRecorder.isTypeSupported !== "function") {
    return undefined;
  }

  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate));
}

export function usePushToTalk({ onTranscript, onError }: UsePushToTalkOptions) {
  const [enabled, setEnabled] = useState(false);
  const [state, setState] = useState<PushToTalkState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const holdActiveRef = useRef(false);

  useEffect(() => {
    let active = true;

    async function loadStatus() {
      try {
        const status = await fetchSttStatus();
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

  const cleanupStream = useCallback(() => {
    for (const track of mediaStreamRef.current?.getTracks() ?? []) {
      track.stop();
    }

    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
  }, []);

  useEffect(() => cleanupStream, [cleanupStream]);

  const fail = useCallback(
    (message: string) => {
      setState("error");
      setErrorMessage(message);
      onError?.(message);
      cleanupStream();
    },
    [cleanupStream, onError],
  );

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      holdActiveRef.current = false;
      cleanupStream();
      setState("idle");
      return;
    }

    holdActiveRef.current = false;
    setState("transcribing");

    const blob = await new Promise<Blob>((resolve, reject) => {
      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "audio/webm";
        resolve(new Blob(chunksRef.current, { type: mimeType }));
      };
      recorder.onerror = () => reject(new Error("Recording failed."));
      recorder.stop();
    }).catch((error: unknown) => {
      const message = error instanceof Error ? error.message : "Recording failed.";
      fail(message);
      return null;
    });

    cleanupStream();

    if (!blob || blob.size === 0) {
      fail("No audio captured.");
      return;
    }

    try {
      const result = await transcribeAudio(blob);
      setErrorMessage(null);
      setState("idle");
      await onTranscript(result.text);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Transcription failed.";
      fail(message);
    }
  }, [cleanupStream, fail, onTranscript]);

  const startRecording = useCallback(async () => {
    if (!enabled || state === "recording" || state === "transcribing") {
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      fail("This browser does not support push-to-talk recording.");
      return;
    }

    setErrorMessage(null);
    holdActiveRef.current = true;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!holdActiveRef.current) {
        for (const track of stream.getTracks()) {
          track.stop();
        }
        return;
      }

      const mimeType = pickMimeType();
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;
      recorder.start();
      setState("recording");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Microphone permission was denied.";
      fail(message);
    }
  }, [enabled, fail, state]);

  const handleHoldStart = useCallback(() => {
    void startRecording();
  }, [startRecording]);

  const handleHoldEnd = useCallback(() => {
    if (state !== "recording") {
      holdActiveRef.current = false;
      return;
    }

    void stopRecording();
  }, [state, stopRecording]);

  const pointerActiveRef = useRef(false);

  const handlePointerDown = useCallback(
    (event: PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      pointerActiveRef.current = true;
      handleHoldStart();
    },
    [handleHoldStart],
  );

  const handlePointerUp = useCallback(() => {
    pointerActiveRef.current = false;
    handleHoldEnd();
  }, [handleHoldEnd]);

  const handleMouseDown = useCallback(
    (event: MouseEvent<HTMLButtonElement>) => {
      if (pointerActiveRef.current || event.button !== 0) {
        return;
      }

      event.preventDefault();
      handleHoldStart();
    },
    [handleHoldStart],
  );

  const handleMouseUp = useCallback(() => {
    if (pointerActiveRef.current) {
      return;
    }

    handleHoldEnd();
  }, [handleHoldEnd]);

  return {
    enabled,
    state,
    errorMessage,
    handlePointerDown,
    handlePointerUp,
    handlePointerLeave: handlePointerUp,
    handlePointerCancel: handlePointerUp,
    handleMouseDown,
    handleMouseUp,
    handleMouseLeave: handleMouseUp,
  };
}
