import { useCallback, useRef } from "react";
import { startPipecat } from "./pipecatApi";

export type WebRtcVoiceConnection = {
  connect: () => Promise<void>;
  disconnect: () => void;
};

const ICE_GATHERING_TIMEOUT_MS = 10_000;

/** Non-trickle ICE: wait for gathering to finish so localDescription.sdp carries candidates. */
export function waitForIceGatheringComplete(
  pc: Pick<RTCPeerConnection, "iceGatheringState" | "addEventListener" | "removeEventListener">,
  timeoutMs: number = ICE_GATHERING_TIMEOUT_MS,
): Promise<void> {
  if (pc.iceGatheringState === "complete") {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const onChange = () => {
      if (pc.iceGatheringState === "complete") {
        cleanup();
        resolve();
      }
    };
    const timer = setTimeout(() => {
      cleanup();
      reject(new Error("ICE gathering timed out"));
    }, timeoutMs);
    function cleanup() {
      clearTimeout(timer);
      pc.removeEventListener("icegatheringstatechange", onChange);
    }
    pc.addEventListener("icegatheringstatechange", onChange);
  });
}

function toError(err: unknown, contextMessage: string): Error {
  const detail = err instanceof Error ? err.message : String(err);
  return new Error(`${contextMessage}: ${detail}`);
}

export function useWebRtcVoiceConnection(): WebRtcVoiceConnection {
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);

  const cleanup = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (pcRef.current) {
      pcRef.current.onconnectionstatechange = null;
      pcRef.current.ontrack = null;
      pcRef.current.close();
      pcRef.current = null;
    }
    if (remoteAudioRef.current) {
      remoteAudioRef.current.pause();
      remoteAudioRef.current.srcObject = null;
      remoteAudioRef.current = null;
    }
  }, []);

  const connect = useCallback(async () => {
    cleanup();

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: false, autoGainControl: false },
      });
    } catch (err) {
      throw toError(err, "Microphone access denied");
    }
    streamRef.current = stream;

    // Mirrors audioUnlock.ts's existing pattern: a detached Audio() element
    // played from within the same user-gesture call stack as the start button.
    const remoteAudio = new Audio();
    remoteAudioRef.current = remoteAudio;

    const pc = new RTCPeerConnection();
    pcRef.current = pc;
    stream.getTracks().forEach((track) => pc.addTrack(track, stream));

    pc.ontrack = (event) => {
      remoteAudio.srcObject = event.streams[0] ?? null;
      void remoteAudio.play().catch(() => {
        // Autoplay may be blocked until the next user gesture; non-fatal.
      });
    };

    pc.onconnectionstatechange = () => {
      if (pc.connectionState === "failed" || pc.connectionState === "closed") {
        cleanup();
      }
    };

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await waitForIceGatheringComplete(pc);

      const localDescription = pc.localDescription;
      if (!localDescription) {
        throw new Error("RTCPeerConnection produced no local description");
      }

      const answer = await startPipecat({
        sdp: localDescription.sdp,
        type: localDescription.type,
      });

      await pc.setRemoteDescription({
        sdp: answer.sdp,
        type: answer.type as RTCSdpType,
      });
    } catch (err) {
      cleanup();
      throw toError(err, "WebRTC handshake failed");
    }
  }, [cleanup]);

  const disconnect = useCallback(() => {
    cleanup();
  }, [cleanup]);

  return { connect, disconnect };
}
