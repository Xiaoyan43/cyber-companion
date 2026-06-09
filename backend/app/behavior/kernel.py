from __future__ import annotations

from backend.app.memory.database import utc_now_iso
from backend.app.memory.store import MemoryStore


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clamp_delta(value: float) -> float:
    return max(-0.1, min(0.1, value))


def _as_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def apply_signals_to_kernel(store: MemoryStore, signals: dict | None) -> None:
    """Apply LLM appraisal + relationship deltas to mood_state + relationship_state.

    Deterministic, clamped, best-effort (never raises into the request path).
    """
    try:
        mood = store.get_mood_state()
        relationship = store.get_relationship_state()

        payload = signals if isinstance(signals, dict) else {}
        appraisal = payload.get("appraisal") if isinstance(payload.get("appraisal"), dict) else {}
        rel = payload.get("relationship") if isinstance(payload.get("relationship"), dict) else {}

        valence = _as_float(appraisal.get("valence"), 0.0)
        goal_relevance = _clamp01(_as_float(appraisal.get("goal_relevance"), 0.0))

        annoyance = mood.annoyance
        boredom = mood.boredom
        worry = mood.worry
        loneliness = mood.loneliness

        if valence < 0 and goal_relevance > 0:
            worry = _clamp01(worry + (-valence) * goal_relevance * 0.10)
        elif valence > 0:
            worry = _clamp01(worry * 0.9)
            boredom = _clamp01(boredom * 0.95)

        trust = relationship.trust
        closeness = relationship.closeness
        familiarity = relationship.familiarity
        tension = relationship.tension

        if "trust" in rel:
            trust = _clamp01(trust + _clamp_delta(_as_float(rel.get("trust"))))
        if "closeness" in rel:
            closeness = _clamp01(closeness + _clamp_delta(_as_float(rel.get("closeness"))))
        rel_raised_tension = False
        if "tension" in rel:
            delta = _clamp_delta(_as_float(rel.get("tension")))
            if delta > 0:
                rel_raised_tension = True
            tension = _clamp01(tension + delta)

        if valence > 0 and goal_relevance > 0:
            closeness = _clamp01(closeness + 0.02)
            trust = _clamp01(trust + 0.01)

        familiarity = _clamp01(familiarity + 0.01)

        if not rel_raised_tension:
            tension = _clamp01(tension * 0.9)

        meaningful_at = relationship.last_meaningful_interaction_at
        if goal_relevance >= 0.5 or abs(valence) >= 0.5:
            meaningful_at = utc_now_iso()
            loneliness = _clamp01(loneliness - 0.1)

        store.update_mood_state(
            worry=round(worry, 3),
            boredom=round(boredom, 3),
            loneliness=round(loneliness, 3),
        )
        store.update_relationship_state(
            trust=round(trust, 3),
            closeness=round(closeness, 3),
            familiarity=round(familiarity, 3),
            tension=round(tension, 3),
            last_meaningful_interaction_at=meaningful_at,
        )
    except Exception:
        return
