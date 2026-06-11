import { describe, expect, it } from "vitest";

import { buildVikingMemoryBadgeView } from "./vikingMemoryBadge";

describe("buildVikingMemoryBadgeView", () => {
  it("reports off when Viking memory is disabled", () => {
    const view = buildVikingMemoryBadgeView({ enabled: false, writeReady: false });
    expect(view.label).toBe("长期记忆 关");
    expect(view.tone).toBe("off");
  });

  it("reports ready when read and write are configured", () => {
    const view = buildVikingMemoryBadgeView({
      enabled: true,
      writeReady: true,
      userId: "boxi_user",
    });
    expect(view.label).toBe("长期记忆 就绪");
    expect(view.tone).toBe("ready");
    expect(view.hint).toContain("boxi_user");
  });

  it("prioritizes save feedback over idle ready state", () => {
    const view = buildVikingMemoryBadgeView({
      enabled: true,
      writeReady: true,
      saveState: "saved",
    });
    expect(view.label).toBe("长期记忆 已写入");
  });
});
