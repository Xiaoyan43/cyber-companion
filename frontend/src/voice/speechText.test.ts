import { describe, expect, it } from "vitest";

import {
  normalizeSpeechText,
  stripStageDirections,
  textChunksForSpeech,
  textForSpeech,
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

describe("textForSpeech", () => {
  it("strips stage directions before synthesis text is returned", () => {
    expect(textForSpeech("（歪头笑出声）行吧，你赢了。", 500)).toBe("行吧，你赢了。");
  });

  it("returns empty when the reply is only stage directions", () => {
    expect(textForSpeech("（沉默三秒）", 500)).toBe("");
  });

  it("keeps quoted content intact", () => {
    expect(textForSpeech('（停顿）够不够"dźwięk"？', 500)).toBe('够不够"dźwięk"？');
  });

  it("returns only the first chunk for long replies", () => {
    const long = "第一句很长。".repeat(20);
    const chunks = textChunksForSpeech(long, 30);
    expect(chunks.length).toBeGreaterThan(1);
    expect(textForSpeech(long, 30)).toBe(chunks[0]);
    expect(chunks.join("")).toContain("第一句很长。");
  });
});

describe("textChunksForSpeech", () => {
  it("chunks stripped speech text instead of raw stage directions", () => {
    const chunks = textChunksForSpeech("（歪头）第一句。第二句。", 6);

    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.join("")).toBe("第一句。第二句。");
    expect(chunks.join("")).not.toContain("歪头");
  });
});
