import type { AvatarState } from "./types";
import { avatarStateDuration } from "./timing";

/** Extra hold so proactive avatar state isn't immediately overwritten by idle rest. */
export const PROACTIVE_HOLD_BONUS_MS = 1400;

/** How long companion/chat attention cues stay visible. */
export const PROACTIVE_ATTENTION_MS = 2800;

export function proactiveAvatarHoldDuration(state: AvatarState, text: string): number {
  return avatarStateDuration(state, text) + PROACTIVE_HOLD_BONUS_MS;
}

export function resolveBehaviorMessageId(
  savedMessageId: number | null | undefined,
  allocateId: () => number,
): number {
  if (typeof savedMessageId === "number") {
    return savedMessageId;
  }

  return allocateId();
}

export function shouldSkipDuplicateBehaviorMessage(
  messages: { id: number }[],
  messageId: number,
): boolean {
  return messages.some((message) => message.id === messageId);
}
