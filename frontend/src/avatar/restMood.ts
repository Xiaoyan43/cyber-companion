import type { MoodStateResponse } from "../api/mood";
import type { AvatarState } from "./types";

export const MOOD_POLL_MS = Number(import.meta.env.VITE_MOOD_POLL_MS) || 75_000;

export const REST_MOOD_THRESHOLDS = {
  energyLow: 0.35,
  boredomHigh: 0.55,
  lonelinessHigh: 0.55,
} as const;

const REST_AVATAR_STATES = new Set<AvatarState>(["idle", "sleepy", "annoyed", "worried"]);

export function isRestAvatarState(state: AvatarState): boolean {
  return REST_AVATAR_STATES.has(state);
}

export function moodToRestState(mood: Pick<MoodStateResponse, "energy" | "boredom" | "loneliness">): AvatarState {
  if (mood.energy < REST_MOOD_THRESHOLDS.energyLow) {
    return "sleepy";
  }

  if (mood.boredom >= REST_MOOD_THRESHOLDS.boredomHigh) {
    return "annoyed";
  }

  if (mood.loneliness >= REST_MOOD_THRESHOLDS.lonelinessHigh) {
    return "worried";
  }

  return "idle";
}
