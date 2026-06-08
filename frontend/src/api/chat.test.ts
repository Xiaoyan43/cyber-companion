import { afterEach, describe, expect, it, vi } from "vitest";

import {
  parseSseDataLine,
  processSseLines,
  requestChatStream,
  type ChatStreamHandlers,
} from "./chat";

describe("parseSseDataLine", () => {
  it("parses data lines and ignores comments or blanks", () => {
    expect(parseSseDataLine('data: {"type":"delta","text":"你"}')).toEqual({
      type: "delta",
      text: "你",
    });
    expect(parseSseDataLine(": keep-alive")).toBeNull();
    expect(parseSseDataLine("")).toBeNull();
  });
});

describe("processSseLines", () => {
  it("handles chunked SSE input across line boundaries", () => {
    const events: Record<string, unknown>[] = [];
    let remainder = processSseLines('data: {"type":"delta","text":"he', () => {});
    remainder = processSseLines(`${remainder}llo"}\n`, (event) => {
      events.push(event);
    });

    expect(remainder).toBe("");
    expect(events).toEqual([{ type: "delta", text: "hello" }]);
  });
});

describe("requestChatStream", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("invokes delta and done handlers from an SSE body", async () => {
    const sseBody = [
      'data: {"type":"delta","text":"你"}',
      "",
      'data: {"type":"delta","text":"好"}',
      "",
      'data: {"type":"done","meta":{"provider":"mock","model":"mock-boxi","decision":"reply","avatar_state":"talking","should_call_llm":true,"usage":{"input_tokens":3,"output_tokens":2,"total_tokens":5},"cost":{"input_usd":0,"output_usd":0,"total_usd":0,"pricing_source":"mock-provider"}}}',
      "",
    ].join("\n");

    const handlers: ChatStreamHandlers = {
      onDelta: vi.fn(),
      onDone: vi.fn(),
      onError: vi.fn(),
    };

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        body: new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode(sseBody));
            controller.close();
          },
        }),
      }),
    );

    const result = await requestChatStream("你好", handlers);

    expect(handlers.onDelta).toHaveBeenCalledTimes(2);
    expect(handlers.onDelta).toHaveBeenNthCalledWith(1, "你");
    expect(handlers.onDelta).toHaveBeenNthCalledWith(2, "好");
    expect(handlers.onDone).toHaveBeenCalledTimes(1);
    expect(handlers.onError).not.toHaveBeenCalled();
    expect(result.content).toBe("你好");
    expect(result.meta.provider).toBe("mock");
  });

  it("throws when the stream emits an error event", async () => {
    const sseBody = 'data: {"type":"error","message":"provider blew up"}\n\n';

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        body: new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode(sseBody));
            controller.close();
          },
        }),
      }),
    );

    await expect(
      requestChatStream("你好", {
        onDelta: vi.fn(),
        onDone: vi.fn(),
        onError: vi.fn(),
      }),
    ).rejects.toThrow("provider blew up");
  });
});
