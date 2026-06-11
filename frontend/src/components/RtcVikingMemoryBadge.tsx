import {
  buildVikingMemoryBadgeView,
  type VikingMemorySaveState,
} from "../rtc/vikingMemoryBadge";

type RtcVikingMemoryBadgeProps = {
  enabled: boolean;
  writeReady: boolean;
  userId?: string;
  saveState?: VikingMemorySaveState;
};

export function RtcVikingMemoryBadge({
  enabled,
  writeReady,
  userId,
  saveState = "idle",
}: RtcVikingMemoryBadgeProps) {
  const view = buildVikingMemoryBadgeView({
    enabled,
    writeReady,
    userId,
    saveState,
  });

  return (
    <span
      className={`rtc-viking-badge tone-${view.tone}`}
      title={view.hint}
      aria-label={view.hint}
    >
      {view.label}
    </span>
  );
}
