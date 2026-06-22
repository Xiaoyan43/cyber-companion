from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from backend.app.behavior.tick_policy import _parse_iso_timestamp
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MoodStateRecord, RelationshipStateRecord

_DEFAULT_CHECK_INTERVAL_SECONDS = 300.0
_PROACTIVE_CHECKIN_LINE = "嘿。你在吗。盒子里有点闷。"


@dataclass(frozen=True)
class LongingSnapshot:
    intensity: float
    lambda_rate: float
    fire_probability: float
    delta_seconds: float


@dataclass(frozen=True)
class ProactiveGateResult:
    blocked: bool
    reason: str | None = None


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _aware_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now().astimezone()
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


def _hours_since(iso_timestamp: str | None, *, now: datetime) -> float | None:
    parsed = _parse_iso_timestamp(iso_timestamp)
    if parsed is None:
        return None
    delta = now.astimezone(timezone.utc) - parsed.astimezone(timezone.utc)
    return max(0.0, delta.total_seconds() / 3600.0)


def compute_longing_intensity(
    *,
    closeness: float,
    loneliness: float,
    last_meaningful_interaction_at: str | None,
    now: datetime | None = None,
    silence_hours_scale: float,
    closeness_weight: float,
    loneliness_weight: float,
) -> float:
    """Longing L in [0,1]: silence scaled by closeness plus current loneliness.

    Unlike idle loneliness drift (which rises faster at *low* closeness), longing
    from silence grows with closeness — you miss someone more when you're close.
    """
    aware = _aware_now(now)
    silence_hours = _hours_since(last_meaningful_interaction_at, now=aware)
    if silence_hours is None or silence_hours_scale <= 0:
        silence_component = 0.0
    else:
        silence_component = min(1.0, silence_hours / silence_hours_scale) * _clamp01(closeness)

    weight_sum = closeness_weight + loneliness_weight
    if weight_sum <= 0:
        return 0.0

    blended = (
        closeness_weight * silence_component + loneliness_weight * _clamp01(loneliness)
    ) / weight_sum
    return round(_clamp01(blended), 4)


def compute_longing_tier(
    *,
    last_meaningful_interaction_at: str | None,
    closeness: float,
    budget: BudgetConfig,
    now: datetime | None = None,
) -> str:
    """Longing trajectory tier: "bored" -> "longing" -> "sulk".

    Floor is "bored", ceiling is "sulk" — never "cold/withdrawn" (no such tier
    exists by construction). "sulk" additionally requires high closeness: you
    only sulk at someone you're actually close to, not at mere silence.
    """
    aware = _aware_now(now)
    silence_hours = _hours_since(last_meaningful_interaction_at, now=aware)
    if silence_hours is None:
        return "bored"

    if (
        silence_hours >= budget.longing_tier_sulk_hours
        and _clamp01(closeness) >= budget.longing_tier_sulk_closeness_min
    ):
        return "sulk"
    if silence_hours >= budget.longing_tier_longing_hours:
        return "longing"
    return "bored"


def compute_lambda_rate(*, longing: float, budget: BudgetConfig) -> float:
    """Poisson rate λ (per second); rises with longing intensity."""
    base_per_hour = max(0.0, budget.longing_lambda_base_per_hour)
    gain = max(0.0, budget.longing_lambda_longing_gain)
    longing_clamped = _clamp01(longing)
    per_hour = base_per_hour * (1.0 + gain * longing_clamped)
    return per_hour / 3600.0


def poisson_fire_probability(*, lambda_rate: float, delta_seconds: float) -> float:
    if lambda_rate <= 0 or delta_seconds <= 0:
        return 0.0
    return _clamp01(1.0 - math.exp(-lambda_rate * delta_seconds))


def _in_quiet_hours(now: datetime, start_hour: int, end_hour: int) -> bool:
    hour = now.hour
    if start_hour == end_hour:
        return False
    if start_hour < end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def _daily_proactive_count(metadata: dict[str, object], *, now: datetime) -> int:
    today = now.date().isoformat()
    if metadata.get("proactive_daily_date") != today:
        return 0
    raw = metadata.get("proactive_daily_count", 0)
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def has_pending_proactive_reply(metadata: dict[str, object]) -> bool:
    return bool(metadata.get("proactive_pending_since"))


def clear_proactive_pending(metadata: dict[str, object]) -> dict[str, object]:
    if "proactive_pending_since" not in metadata:
        return metadata
    updated = dict(metadata)
    updated.pop("proactive_pending_since", None)
    return updated


def check_proactive_availability(
    *,
    budget: BudgetConfig,
    mood: MoodStateRecord,
    relationship: RelationshipStateRecord,
    last_user_message_at: str | None,
    now: datetime | None = None,
    skip_timing_gates: bool = False,
) -> ProactiveGateResult:
    aware = _aware_now(now)

    if not budget.enable_proactive:
        return ProactiveGateResult(blocked=True, reason="proactive_disabled")

    if has_pending_proactive_reply(mood.metadata):
        return ProactiveGateResult(blocked=True, reason="awaiting_user_reply")

    if not skip_timing_gates:
        fire_gap_hours = max(0.0, budget.proactive_min_fire_gap_hours)
        if fire_gap_hours > 0:
            hours_since_fire = _hours_since(
                str(mood.metadata.get("last_proactive_fired_at") or ""),
                now=aware,
            )
            if hours_since_fire is not None and hours_since_fire < fire_gap_hours:
                return ProactiveGateResult(blocked=True, reason="proactive_fire_gap")

        gap_minutes = max(0, budget.proactive_min_gap_minutes)
        if gap_minutes > 0:
            last_user = _parse_iso_timestamp(last_user_message_at)
            if last_user is not None:
                elapsed_minutes = (aware.astimezone(timezone.utc) - last_user.astimezone(timezone.utc)).total_seconds() / 60.0
                if elapsed_minutes < gap_minutes:
                    return ProactiveGateResult(blocked=True, reason="post_conversation_cooldown")

        quiet = budget.proactive_quiet_hours
        if len(quiet) >= 2 and _in_quiet_hours(aware, int(quiet[0]), int(quiet[1])):
            return ProactiveGateResult(blocked=True, reason="quiet_hours")

    daily_max = max(0, budget.proactive_daily_max)
    if daily_max > 0 and _daily_proactive_count(mood.metadata, now=aware) >= daily_max:
        return ProactiveGateResult(blocked=True, reason="proactive_daily_cap")

    return ProactiveGateResult(blocked=False)


def _resolve_delta_seconds(
    metadata: dict[str, object],
    *,
    now: datetime,
    max_delta_seconds: float | None = None,
) -> float:
    last_check = _parse_iso_timestamp(metadata.get("last_proactive_check_at"))
    if last_check is None:
        elapsed = _DEFAULT_CHECK_INTERVAL_SECONDS
    else:
        elapsed = (now.astimezone(timezone.utc) - last_check.astimezone(timezone.utc)).total_seconds()
        elapsed = max(1.0, elapsed)
    if max_delta_seconds is not None and max_delta_seconds > 0:
        return min(elapsed, max_delta_seconds)
    return elapsed


def mark_proactive_check(metadata: dict[str, object], *, now: datetime) -> dict[str, object]:
    updated = dict(metadata)
    updated["last_proactive_check_at"] = now.astimezone(timezone.utc).isoformat()
    return updated


def mark_proactive_fired(metadata: dict[str, object], *, now: datetime) -> dict[str, object]:
    updated = mark_proactive_check(metadata, now=now)
    fired_at = now.astimezone(timezone.utc).isoformat()
    updated["last_proactive_fired_at"] = fired_at
    updated["proactive_pending_since"] = fired_at
    today = now.date().isoformat()
    if updated.get("proactive_daily_date") != today:
        updated["proactive_daily_date"] = today
        updated["proactive_daily_count"] = 1
    else:
        updated["proactive_daily_count"] = _daily_proactive_count(updated, now=now) + 1
    return updated


def snapshot_longing(
    *,
    closeness: float,
    loneliness: float,
    last_meaningful_interaction_at: str | None,
    metadata: dict[str, object],
    budget: BudgetConfig,
    now: datetime | None = None,
) -> LongingSnapshot:
    aware = _aware_now(now)
    intensity = compute_longing_intensity(
        closeness=closeness,
        loneliness=loneliness,
        last_meaningful_interaction_at=last_meaningful_interaction_at,
        now=aware,
        silence_hours_scale=budget.longing_silence_hours_scale,
        closeness_weight=budget.longing_closeness_weight,
        loneliness_weight=budget.longing_loneliness_weight,
    )
    delta_seconds = _resolve_delta_seconds(
        metadata,
        now=aware,
        max_delta_seconds=budget.proactive_max_delta_seconds,
    )
    lambda_rate = compute_lambda_rate(longing=intensity, budget=budget)
    fire_probability = poisson_fire_probability(lambda_rate=lambda_rate, delta_seconds=delta_seconds)
    return LongingSnapshot(
        intensity=intensity,
        lambda_rate=lambda_rate,
        fire_probability=fire_probability,
        delta_seconds=delta_seconds,
    )


def should_fire_longing(
    snapshot: LongingSnapshot,
    *,
    rng: random.Random | None = None,
    roll: Callable[[], float] | None = None,
) -> bool:
    if snapshot.fire_probability <= 0:
        return False
    drawn = roll() if roll is not None else (rng or random.Random()).random()
    return drawn < snapshot.fire_probability


def proactive_checkin_line() -> str:
    return _PROACTIVE_CHECKIN_LINE
