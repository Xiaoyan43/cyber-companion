import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchPipecatStatus, startPipecat, stopPipecat } from "./pipecatApi";

describe("Pipecat voice API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("reads pipeline status including startup errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "stopped", last_error: "missing config" }),
      }),
    );

    await expect(fetchPipecatStatus()).resolves.toEqual({
      status: "stopped",
      last_error: "missing config",
    });
  });

  it("posts the SDP offer and resolves the SDP answer", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ sdp: "v=0 answer...", type: "answer", pc_id: "abc123" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const offer = { sdp: "v=0 offer...", type: "offer" };
    await expect(startPipecat(offer)).resolves.toEqual({
      sdp: "v=0 answer...",
      type: "answer",
      pc_id: "abc123",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/realtime/start"),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(offer),
      },
    );
  });

  it("uses POST for stop", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "stopped" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await stopPipecat();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/realtime/stop"),
      { method: "POST" },
    );
  });

  it("rejects non-success responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));

    await expect(startPipecat({ sdp: "v=0", type: "offer" })).rejects.toThrow(
      "Soul voice request failed (503)",
    );
  });
});
