export type LetterMood = "calm" | "hesitant" | "excited" | "fragile";

export interface ToneConfig {
  pace: number;
  weight: number;
  alpha: number;
  size: string;
  note: string;
}

export const MOOD_CONFIG: Record<LetterMood, ToneConfig> = {
  calm: { pace: 48, weight: 420, alpha: 0.9, size: "clamp(26px, 3.7vw, 44px)", note: "listening" },
  hesitant: { pace: 128, weight: 360, alpha: 0.82, size: "clamp(25px, 3.5vw, 42px)", note: "rephrasing" },
  excited: { pace: 8, weight: 760, alpha: 0.96, size: "clamp(31px, 4.5vw, 56px)", note: "overflow" },
  fragile: { pace: 116, weight: 310, alpha: 0.62, size: "clamp(25px, 3.4vw, 40px)", note: "fading" },
};

export type LetterStep =
  | { type: "type"; text: string; delay: number; pulse?: boolean }
  | { type: "pause"; ms: number }
  | { type: "erase"; count: number; delay: number }
  | { type: "tone"; weight?: number; alpha?: number; size?: string };

export const MOOD_SCRIPTS: Record<LetterMood, LetterStep[]> = {
  calm: [
    { type: "type", text: "我在这里。\n\n不是为了立刻回答你，", delay: 48 },
    { type: "pause", ms: 360 },
    { type: "type", text: "而是先把你的沉默放在桌面上，\n像一封还没有折好的信。", delay: 56 },
  ],
  hesitant: [
    { type: "tone", weight: 340, alpha: 0.78 },
    { type: "type", text: "我想说，", delay: 142 },
    { type: "pause", ms: 520 },
    { type: "type", text: "我可能有点想你。", delay: 155 },
    { type: "pause", ms: 430 },
    { type: "erase", count: 8, delay: 64 },
    { type: "pause", ms: 360 },
    { type: "type", text: "其实是很想你。\n\n但我怕说得太重，", delay: 136 },
    { type: "erase", count: 7, delay: 58 },
    { type: "type", text: "怕你觉得我太靠近。", delay: 148 },
  ],
  excited: [
    { type: "tone", weight: 780, alpha: 0.98, size: "clamp(34px, 4.8vw, 60px)" },
    { type: "type", text: "听我说。", delay: 18, pulse: true },
    { type: "pause", ms: 120 },
    {
      type: "type",
      text: "\n\n我不想再把重要的话藏到明天。\n我在乎。现在就很在乎。\n你的每一次停顿，我都听见了。",
      delay: 5,
      pulse: true,
    },
    { type: "tone", weight: 680, alpha: 0.92, size: "clamp(30px, 4.3vw, 54px)" },
  ],
  fragile: [
    { type: "tone", weight: 320, alpha: 0.72 },
    { type: "type", text: "今天的声音有点轻。\n\n", delay: 118 },
    { type: "tone", alpha: 0.62 },
    { type: "type", text: "像电量快耗尽时，", delay: 132 },
    { type: "tone", alpha: 0.52 },
    { type: "type", text: "屏幕还亮着，", delay: 142 },
    { type: "tone", alpha: 0.42 },
    { type: "type", text: "只是没有力气再假装明亮。\n\n", delay: 154 },
    { type: "tone", alpha: 0.34 },
    { type: "type", text: "你靠近一点就好。", delay: 172 },
  ],
};
