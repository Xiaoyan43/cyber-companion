import { describe, expect, it } from "vitest";

import {
  normalizeSpeechText,
  prepareTextForSpeech,
  stripStageDirections,
} from "./speechText";

describe("stripStageDirections", () => {
  it("removes full-width stage directions", () => {
    expect(stripStageDirections("（歪头笑出声）行吧，你赢了。")).toBe("行吧，你赢了。");
  });

  it("removes half-width stage directions", () => {
    expect(stripStageDirections("(清了清嗓子)成，那您听好了。")).toBe("成，那您听好了。");
  });

  it("removes corner-bracket stage directions", () => {
    expect(stripStageDirections("【歪头】嗯？")).toBe("嗯？");
  });

  it("returns empty when only stage directions remain", () => {
    expect(stripStageDirections("（沉默三秒）")).toBe("");
  });

  it("preserves quoted dialogue", () => {
    expect(stripStageDirections('（动作）你说"Jeszcze dźwięk"对吧？')).toBe(
      '你说"Jeszcze dźwięk"对吧？',
    );
  });
});

describe("normalizeSpeechText", () => {
  it("collapses extra spaces and repeated punctuation", () => {
    expect(normalizeSpeechText("行吧，  ，你赢了。。")).toBe("行吧，你赢了。");
  });
});

describe("prepareTextForSpeech", () => {
  it("strips stage directions before synthesis text is returned", () => {
    expect(prepareTextForSpeech("（歪头笑出声）行吧，你赢了。")).toBe("行吧，你赢了。");
  });

  it("returns empty when the reply is only stage directions", () => {
    expect(prepareTextForSpeech("（沉默三秒）")).toBe("");
  });

  it("keeps quoted content intact", () => {
    expect(prepareTextForSpeech('（停顿）够不够"dźwięk"？')).toBe('够不够"dźwięk"？');
  });

  it("keeps long replies intact instead of truncating them", () => {
    const long = "第一句很长。".repeat(20);
    expect(prepareTextForSpeech(long)).toBe(long);
  });
});
