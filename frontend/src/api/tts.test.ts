import { afterEach, describe, expect, it, vi } from "vitest";

import { buildTtsStreamUrl, probeTtsStream } from "./tts";

describe("buildTtsStreamUrl", () => {
  it("encodes Chinese text and optional query params", () => {
    const url = buildTtsStreamUrl({
      text: "你好，Boxi。",
      decision: "reply",
      avatarState: "talking",
    });

    expect(url).toContain("/tts/stream?");
    expect(url).toContain(`text=${encodeURIComponent("你好，Boxi。")}`);
    expect(url).toContain("decision=reply");
    expect(url).toContain("avatar_state=talking");
  });
});

describe("probeTtsStream", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns skip for HTTP 204", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 204,
        ok: false,
        body: { cancel: vi.fn().mockResolvedValue(undefined) },
      }),
    );

    await expect(probeTtsStream("http://127.0.0.1:8000/tts/stream?text=hi")).resolves.toBe("skip");
  });

  it("returns ok for HTTP 200 and cancels the probe body", async () => {
    const cancel = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        body: { cancel },
      }),
    );

    await expect(probeTtsStream("http://127.0.0.1:8000/tts/stream?text=hi")).resolves.toBe("ok");
    expect(cancel).toHaveBeenCalledOnce();
  });

  it("returns error for HTTP 5xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 503,
        ok: false,
      }),
    );

    await expect(probeTtsStream("http://127.0.0.1:8000/tts/stream?text=hi")).resolves.toBe("error");
  });
});
