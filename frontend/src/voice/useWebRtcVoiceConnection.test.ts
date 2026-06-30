import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { waitForIceGatheringComplete } from "./useWebRtcVoiceConnection";

type FakeIceGatheringState = "new" | "gathering" | "complete";

function createFakePeerConnection(initialState: FakeIceGatheringState) {
  let listener: (() => void) | null = null;
  return {
    iceGatheringState: initialState as RTCPeerConnection["iceGatheringState"],
    addEventListener: vi.fn((_event: string, cb: () => void) => {
      listener = cb;
    }),
    removeEventListener: vi.fn(() => {
      listener = null;
    }),
    setState(next: FakeIceGatheringState) {
      this.iceGatheringState = next as RTCPeerConnection["iceGatheringState"];
      listener?.();
    },
  };
}

describe("waitForIceGatheringComplete", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("resolves immediately when already complete", async () => {
    const pc = createFakePeerConnection("complete");
    await expect(waitForIceGatheringComplete(pc)).resolves.toBeUndefined();
    expect(pc.addEventListener).not.toHaveBeenCalled();
  });

  it("resolves once gathering transitions to complete", async () => {
    const pc = createFakePeerConnection("gathering");
    const promise = waitForIceGatheringComplete(pc);
    pc.setState("complete");
    await expect(promise).resolves.toBeUndefined();
    expect(pc.removeEventListener).toHaveBeenCalled();
  });

  it("ignores transitions that are not yet complete", async () => {
    const pc = createFakePeerConnection("new");
    const promise = waitForIceGatheringComplete(pc);
    pc.setState("gathering");
    pc.setState("complete");
    await expect(promise).resolves.toBeUndefined();
  });

  it("rejects when gathering never completes before the timeout", async () => {
    vi.useFakeTimers();
    const pc = createFakePeerConnection("gathering");
    const promise = waitForIceGatheringComplete(pc, 1000);
    const assertion = expect(promise).rejects.toThrow("ICE gathering timed out");
    await vi.advanceTimersByTimeAsync(1000);
    await assertion;
  });
});

describe("useWebRtcVoiceConnection", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("module exports connect/disconnect hook factory", async () => {
    const mod = await import("./useWebRtcVoiceConnection");
    expect(typeof mod.useWebRtcVoiceConnection).toBe("function");
  });
});
