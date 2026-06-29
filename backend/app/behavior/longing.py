from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from backend.app.behavior.time_utils import parse_iso_timestamp
from backend.app.memory.budget import BudgetConfig

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
    parsed = parse_iso_timestamp(iso_timestamp)
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

    These are intensity labels, not permitted-expression boundaries. The "sulk"
    tier additionally requires high closeness; its authored expression may still
    include neediness, accusation, pressure, or withdrawal.
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


def check_proactive_availability(
    *,
    budget: BudgetConfig,
) -> ProactiveGateResult:
    if not budget.enable_proactive:
        return ProactiveGateResult(blocked=True, reason="proactive_disabled")
    return ProactiveGateResult(blocked=False)


def _resolve_delta_seconds(
    metadata: dict[str, object],
    *,
    now: datetime,
) -> float:
    last_check = parse_iso_timestamp(metadata.get("last_proactive_check_at"))
    if last_check is None:
        elapsed = _DEFAULT_CHECK_INTERVAL_SECONDS
    else:
        elapsed = (now.astimezone(timezone.utc) - last_check.astimezone(timezone.utc)).total_seconds()
        elapsed = max(1.0, elapsed)
    return elapsed


def mark_proactive_check(metadata: dict[str, object], *, now: datetime) -> dict[str, object]:
    updated = dict(metadata)
    updated["last_proactive_check_at"] = now.astimezone(timezone.utc).isoformat()
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
    delta_seconds = _resolve_delta_seconds(metadata, now=aware)
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
