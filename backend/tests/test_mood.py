from datetime import datetime, timedelta, timezone

from backend.app.behavior.mood import apply_interaction_slow_delta, apply_slow_baseline_decay
from backend.app.memory.database import MoodStateRecord

_BASE_AT = "2026-06-10T00:00:00+00:00"


def _make_mood(
    *,
    gap_feeling: float = 0.5,
    box_relation: float = 0.5,
    self_ease: float = 0.5,
    energy: float = 0.7,
    annoyance: float = 0.1,
) -> MoodStateRecord:
    return MoodStateRecord(
        updated_at=_BASE_AT,
        mood="idle",
        energy=energy,
        annoyance=annoyance,
        boredom=0.0,
        worry=0.0,
        trust=0.5,
        loneliness=0.2,
        gap_feeling=gap_feeling,
        box_relation=box_relation,
        self_ease=self_ease,
    )


_NOW = datetime.fromisoformat(_BASE_AT)


# --- apply_slow_baseline_decay ---


def test_decay_zero_elapsed_no_change() -> None:
    mood = _make_mood(gap_feeling=0.8, box_relation=0.6, self_ease=0.7)
    result = apply_slow_baseline_decay(mood, now=_NOW)
    assert result.gap_feeling == mood.gap_feeling
    assert result.box_relation == mood.box_relation
    assert result.self_ease == mood.self_ease


def test_decay_seven_days_gap_feeling() -> None:
    mood = _make_mood(gap_feeling=0.8)
    now = _NOW + timedelta(days=7)
    result = apply_slow_baseline_decay(mood, now=now)
    # 0.8 - 7 * 0.04 = 0.52
    assert abs(result.gap_feeling - 0.52) < 1e-9


def test_decay_seven_days_box_relation() -> None:
    mood = _make_mood(box_relation=0.6)
    now = _NOW + timedelta(days=7)
    result = apply_slow_baseline_decay(mood, now=now)
    # 0.6 - 7 * 0.01 = 0.53
    assert abs(result.box_relation - 0.53) < 1e-9


def test_decay_seven_days_self_ease() -> None:
    mood = _make_mood(self_ease=0.7)
    now = _NOW + timedelta(days=7)
    result = apply_slow_baseline_decay(mood, now=now)
    # 0.7 - 7 * 0.005 = 0.665
    assert abs(result.self_ease - 0.665) < 1e-9


def test_decay_clamps_at_zero() -> None:
    mood = _make_mood(gap_feeling=0.1, box_relation=0.05, self_ease=0.02)
    now = _NOW + timedelta(days=30)
    result = apply_slow_baseline_decay(mood, now=now)
    assert result.gap_feeling == 0.0
    assert result.box_relation == 0.0
    assert result.self_ease == 0.0


def test_decay_does_not_affect_fast_mood_fields() -> None:
    mood = _make_mood(energy=0.7, annoyance=0.1)
    now = _NOW + timedelta(days=7)
    result = apply_slow_baseline_decay(mood, now=now)
    assert result.energy == mood.energy
    assert result.annoyance == mood.annoyance
    assert result.boredom == mood.boredom
    assert result.loneliness == mood.loneliness
    assert result.mood == mood.mood


def test_decay_naive_updated_at_treated_as_utc() -> None:
    naive_mood = MoodStateRecord(
        updated_at="2026-06-10T00:00:00",  # no tz suffix
        mood="idle",
        energy=0.7,
        annoyance=0.0,
        boredom=0.0,
        worry=0.0,
        trust=0.5,
        loneliness=0.0,
        gap_feeling=0.8,
        box_relation=0.6,
        self_ease=0.5,
    )
    now = datetime(2026, 6, 17, 0, 0, 0, tzinfo=timezone.utc)
    result = apply_slow_baseline_decay(naive_mood, now=now)
    # 7 days elapsed
    assert abs(result.gap_feeling - 0.52) < 1e-9


# --- apply_interaction_slow_delta ---


def test_positive_turn_raises_all_dims() -> None:
    mood = _make_mood(gap_feeling=0.5, box_relation=0.5, self_ease=0.5)
    result = apply_interaction_slow_delta(mood, positive_turn=True)
    assert abs(result.gap_feeling - 0.58) < 1e-9
    assert abs(result.box_relation - 0.54) < 1e-9
    assert abs(result.self_ease - 0.52) < 1e-9


def test_negative_turn_lowers_all_dims() -> None:
    mood = _make_mood(gap_feeling=0.5, box_relation=0.5, self_ease=0.5)
    result = apply_interaction_slow_delta(mood, positive_turn=False)
    assert abs(result.gap_feeling - 0.46) < 1e-9
    assert abs(result.box_relation - 0.48) < 1e-9
    assert abs(result.self_ease - 0.49) < 1e-9


def test_positive_turn_clamps_at_one() -> None:
    mood = _make_mood(gap_feeling=0.98, box_relation=0.98, self_ease=0.99)
    result = apply_interaction_slow_delta(mood, positive_turn=True)
    assert result.gap_feeling == 1.0
    assert result.box_relation == 1.0
    assert result.self_ease == 1.0


def test_negative_turn_clamps_at_zero() -> None:
    mood = _make_mood(gap_feeling=0.02, box_relation=0.01, self_ease=0.005)
    result = apply_interaction_slow_delta(mood, positive_turn=False)
    assert result.gap_feeling == 0.0
    assert result.box_relation == 0.0
    assert result.self_ease == 0.0


def test_interaction_delta_does_not_affect_fast_mood_fields() -> None:
    mood = _make_mood(energy=0.7, annoyance=0.3)
    result = apply_interaction_slow_delta(mood, positive_turn=True)
    assert result.energy == mood.energy
    assert result.annoyance == mood.annoyance
    assert result.boredom == mood.boredom
    assert result.loneliness == mood.loneliness
    assert result.mood == mood.mood
