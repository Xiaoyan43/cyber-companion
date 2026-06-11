import { describe, expect, it } from "vitest";
import { createRtcMessageState, detectCompletedTurn, parseRtcRoomMessage } from "./rtcMessages";
import { string2tlv } from "./tlv";

describe("parseRtcRoomMessage", () => {
  it("accumulates subtitle lines for user and bot", () => {
    let state = {
      ...createRtcMessageState(),
      localUserId: "user-1",
      botUserId: "BoxiBot",
      agentEnabled: true,
    };

    const userFrame = string2tlv(
      JSON.stringify({
        data: [{ text: "你好", userId: "user-1", definite: false, paragraph: false }],
      }),
      "subv",
    );
    state = parseRtcRoomMessage(userFrame, state);
    expect(state.lines).toHaveLength(1);
    expect(state.lines[0].speaker).toBe("user");

    const botFrame = string2tlv(
      JSON.stringify({
        data: [{ text: "又醒了。", userId: "BoxiBot", definite: true, paragraph: true }],
      }),
      "subv",
    );
    state = parseRtcRoomMessage(botFrame, state);
    expect(state.lines).toHaveLength(2);
    expect(state.lines[1].speaker).toBe("boxi");
  });

  it("detects a completed user-to-bot exchange when bot subtitle is definite", () => {
    const lines = [
      {
        id: "rtc-line-1",
        speaker: "user" as const,
        text: "你好",
        definite: false,
        paragraph: true,
      },
      {
        id: "rtc-line-2",
        speaker: "boxi" as const,
        text: "又醒了。",
        definite: true,
        paragraph: true,
      },
    ];
    const completed = detectCompletedTurn(lines);
    expect(completed).toEqual({
      userText: "你好",
      botText: "又醒了。",
      turnKey: "rtc-line-1:rtc-line-2",
    });
  });

  it("maps agent brief speaking to agent phase", () => {
    let state = { ...createRtcMessageState(), agentEnabled: true };
    const brief = string2tlv(JSON.stringify({ Stage: { Code: 3 } }), "conv");
    state = parseRtcRoomMessage(brief, state);
    expect(state.agentPhase).toBe("speaking");
  });
});
