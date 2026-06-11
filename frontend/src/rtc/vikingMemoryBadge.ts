export type VikingMemorySaveState = "idle" | "saving" | "saved";

export type VikingMemoryBadgeTone = "off" | "partial" | "ready";

export type VikingMemoryBadgeView = {
  label: string;
  hint: string;
  tone: VikingMemoryBadgeTone;
};

export function buildVikingMemoryBadgeView(options: {
  enabled: boolean;
  writeReady: boolean;
  userId?: string;
  saveState?: VikingMemorySaveState;
}): VikingMemoryBadgeView {
  const { enabled, writeReady, userId, saveState = "idle" } = options;

  if (saveState === "saving") {
    return {
      label: "长期记忆 写入中…",
      hint: "正在把本轮字幕上传到 Viking",
      tone: writeReady ? "ready" : "partial",
    };
  }

  if (saveState === "saved") {
    return {
      label: "长期记忆 已写入",
      hint: userId ? `本轮对话已保存 · 用户 ${userId}` : "本轮对话已保存到 Viking",
      tone: "ready",
    };
  }

  if (writeReady) {
    return {
      label: "长期记忆 就绪",
      hint: userId
        ? `跨会话召回已启用 · 用户 ${userId} · 挂断后自动写入`
        : "跨会话召回已启用 · 挂断后自动写入",
      tone: "ready",
    };
  }

  if (enabled) {
    return {
      label: "长期记忆 只读",
      hint: "已配置记忆库，但缺少写入密钥（VIKING_MEMORY_API_KEY）",
      tone: "partial",
    };
  }

  return {
    label: "长期记忆 关",
    hint: "未配置 VIKING_MEMORY_COLLECTION",
    tone: "off",
  };
}
