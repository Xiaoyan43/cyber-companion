export const avatarTiming = {
  thinkingMs: 700,
  talkingMinMs: 1400,
  talkingMsPerChar: 45,
  talkingMaxMs: 4200,
  annoyedMs: 1600,
  silentMs: 1200,
  worriedMs: 1800,
} as const;

export function talkingDuration(text: string): number {
  const estimated = text.length * avatarTiming.talkingMsPerChar;

  return Math.min(
    avatarTiming.talkingMaxMs,
    Math.max(avatarTiming.talkingMinMs, estimated),
  );
}

export function avatarStateDuration(state: string, text: string): number {
  if (state === "silent") {
    return avatarTiming.silentMs;
  }

  if (state === "annoyed" || state === "angry") {
    return avatarTiming.annoyedMs;
  }

  if (state === "worried") {
    return avatarTiming.worriedMs;
  }

  if (state === "thinking") {
    return avatarTiming.thinkingMs;
  }

  return talkingDuration(text);
}
