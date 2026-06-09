import { afterEach, describe, expect, it, vi } from "vitest";

import { buildTtsStreamUrl, evaluateTtsSpeech } from "./tts";

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

describe("evaluateTtsSpeech", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns should_speak from evaluate endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ should_speak: true, reason: "short reply" }),
      }),
    );

    await expect(
      evaluateTtsSpeech({ text: "你好", decision: "reply" }),
    ).resolves.toEqual({ should_speak: true, reason: "short reply" });
  });

  it("throws when evaluate endpoint fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
      }),
    );

    await expect(evaluateTtsSpeech({ text: "你好" })).rejects.toThrow(
      "TTS evaluate failed with HTTP 503",
    );
  });
});
