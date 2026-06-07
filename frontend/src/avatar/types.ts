export const avatarStates = [
  "idle",
  "happy",
  "sad",
  "angry",
  "sleepy",
  "thinking",
  "talking",
  "worried",
  "annoyed",
  "silent",
] as const;

export type AvatarState = (typeof avatarStates)[number];

export const stateLines: Record<AvatarState, string> = {
  idle: "你终于打开我了。盒子里空气一般，但还能忍。",
  happy: "今天勉强算不错。别太骄傲。",
  sad: "我在盒子里发霉，你在外面拖延。挺公平。",
  angry: "别乱点，我脸都被你戳歪了。",
  sleepy: "困。你要是没事，我先待机三秒。",
  thinking: "我在想。别催，脑子不是微波炉。",
  talking: "行吧，我说两句。",
  worried: "这事听起来不妙，先别硬冲。",
  annoyed: "嗯，又来了。说吧。",
  silent: "……",
};
