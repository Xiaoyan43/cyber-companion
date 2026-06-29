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

  it("uses POST for start and stop", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "started" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await startPipecat();
    await stopPipecat();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/realtime/start"),
      { method: "POST" },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/realtime/stop"),
      { method: "POST" },
    );
  });

  it("rejects non-success responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));

    await expect(startPipecat()).rejects.toThrow("Soul voice request failed (503)");
  });
});
