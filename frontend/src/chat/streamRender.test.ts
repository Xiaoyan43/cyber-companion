import { describe, expect, it } from "vitest";

import type { ChatMessage } from "./types";
import { appendChatStreamDelta } from "./streamRender";

describe("appendChatStreamDelta", () => {
  it("appends text to the targeted boxi bubble only", () => {
    const messages: ChatMessage[] = [
      { id: 1, speaker: "user", text: "hi" },
      { id: 2, speaker: "boxi", text: "" },
      { id: 3, speaker: "boxi", text: "other" },
    ];

    const once = appendChatStreamDelta(messages, 2, "你");
    const twice = appendChatStreamDelta(once, 2, "好");

    expect(twice).toEqual([
      { id: 1, speaker: "user", text: "hi" },
      { id: 2, speaker: "boxi", text: "你好" },
      { id: 3, speaker: "boxi", text: "other" },
    ]);
  });
});
