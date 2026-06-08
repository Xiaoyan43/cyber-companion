import { describe, expect, it } from "vitest";

import {
  drainStreamingSpeechChunks,
  flushStreamingSpeechRemainder,
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
});

describe("textChunksForSpeech", () => {
  it("chunks stripped speech text instead of raw stage directions", () => {
    const chunks = textChunksForSpeech("（歪头）第一句。第二句。", 6);

    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.join("")).toBe("第一句。第二句。");
    expect(chunks.join("")).not.toContain("歪头");
  });
});

describe("drainStreamingSpeechChunks", () => {
  it("splits on Chinese sentence boundaries and strips stage directions", () => {
    const first = drainStreamingSpeechChunks("（歪头）第一句。第二", 120);

    expect(first.chunks).toEqual(["第一句。"]);
    expect(first.remainder).toBe("第二");

    const second = drainStreamingSpeechChunks(first.remainder, 120);
    expect(second.chunks).toEqual([]);
    expect(second.remainder).toBe("第二");
  });

  it("splits on newline and western punctuation", () => {
    const newline = drainStreamingSpeechChunks("Hello\nworld", 120);
    expect(newline.chunks).toEqual(["Hello"]);
    expect(newline.remainder).toBe("world");

    const western = drainStreamingSpeechChunks("Hi. There", 120);
    expect(western.chunks).toEqual(["Hi."]);
    expect(western.remainder).toBe("There");
  });

  it("forces max-length splits when no boundary is present", () => {
    const forced = drainStreamingSpeechChunks("a".repeat(25), 10);
    expect(forced.chunks).toEqual(["a".repeat(10), "a".repeat(10)]);
    expect(forced.remainder).toBe("a".repeat(5));
  });
});

describe("flushStreamingSpeechRemainder", () => {
  it("returns stripped remainder as one chunk when short enough", () => {
    expect(flushStreamingSpeechRemainder("（动作）收尾句", 120)).toEqual(["收尾句"]);
  });

  it("chunks an oversized remainder", () => {
    const chunks = flushStreamingSpeechRemainder("第一句。第二句。", 6);
    expect(chunks.join("")).toBe("第一句。第二句。");
  });
});
