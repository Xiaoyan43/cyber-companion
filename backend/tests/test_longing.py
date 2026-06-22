from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.longing import (
    check_proactive_availability,
    compute_longing_intensity,
    compute_longing_tier,
    poisson_fire_probability,
    should_fire_longing,
    snapshot_longing,
)
from backend.app.behavior.types import BehaviorEvent
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MoodStateRecord, RelationshipStateRecord, connect
from backend.app.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "longing.db")


def _quiet_budget(**overrides: object) -> BudgetConfig:
    base = {
        "enable_proactive": True,
        "proactive_min_gap_minutes": 0,
        "proactive_daily_max": 10,
        "proactive_quiet_hours": (0, 0),
        "longing_silence_hours_scale": 24.0,
        "longing_closeness_weight": 0.6,
        "longing_loneliness_weight": 0.4,
        "longing_lambda_base_per_hour": 0.0,
        "longing_lambda_longing_gain": 2.0,
    }
    base.update(overrides)
    return BudgetConfig(**base)


def _hot_budget(**overrides: object) -> BudgetConfig:
    return _quiet_budget(longing_lambda_base_per_hour=80.0, **overrides)


def _mood(**metadata: object) -> MoodStateRecord:
    return MoodStateRecord(
        updated_at="2026-06-13T12:00:00+00:00",
        mood="idle",
        energy=0.5,
        annoyance=0.1,
        boredom=0.2,
        worry=0.1,
        trust=0.5,
        loneliness=0.3,
        metadata=dict(metadata),
    )


def _relationship(
    *,
    closeness: float = 0.2,
    meaningful_at: str | None = None,
) -> RelationshipStateRecord:
    return RelationshipStateRecord(
        updated_at="2026-06-13T12:00:00+00:00",
        trust=0.5,
        closeness=closeness,
        familiarity=0.0,
        tension=0.0,
        last_meaningful_interaction_at=meaningful_at,
        metadata={},
    )


def test_longing_rises_with_closeness_at_same_silence() -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    meaningful = (now - timedelta(hours=12)).isoformat()
    low = compute_longing_intensity(
        closeness=0.2,
        loneliness=0.3,
        last_meaningful_interaction_at=meaningful,
        now=now,
        silence_hours_scale=24.0,
        closeness_weight=0.6,
        loneliness_weight=0.4,
    )
    high = compute_longing_intensity(
        closeness=0.8,
        loneliness=0.3,
        last_meaningful_interaction_at=meaningful,
        now=now,
        silence_hours_scale=24.0,
        closeness_weight=0.6,
        loneliness_weight=0.4,
    )
    assert high > low


def test_longing_rises_with_silence_at_same_closeness() -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    short = compute_longing_intensity(
        closeness=0.7,
        loneliness=0.3,
        last_meaningful_interaction_at=(now - timedelta(hours=2)).isoformat(),
        now=now,
        silence_hours_scale=24.0,
        closeness_weight=0.6,
        loneliness_weight=0.4,
    )
    long = compute_longing_intensity(
        closeness=0.7,
        loneliness=0.3,
        last_meaningful_interaction_at=(now - timedelta(hours=20)).isoformat(),
        now=now,
        silence_hours_scale=24.0,
        closeness_weight=0.6,
        loneliness_weight=0.4,
    )
    assert long > short


def test_poisson_probability_is_deterministic() -> None:
    p1 = poisson_fire_probability(lambda_rate=0.001, delta_seconds=300.0)
    p2 = poisson_fire_probability(lambda_rate=0.001, delta_seconds=300.0)
    assert p1 == p2
    assert 0.0 < p1 < 1.0


def test_seeded_rng_fire_is_deterministic() -> None:
    budget = _quiet_budget(longing_lambda_base_per_hour=0.05)
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    metadata = {"last_proactive_check_at": (now - timedelta(minutes=5)).isoformat()}
    snap = snapshot_longing(
        closeness=0.8,
        loneliness=0.7,
        last_meaningful_interaction_at=(now - timedelta(hours=10)).isoformat(),
        metadata=metadata,
        budget=budget,
        now=now,
    )
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    assert should_fire_longing(snap, rng=rng_a) == should_fire_longing(snap, rng=rng_b)


def test_post_conversation_cooldown_blocks() -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    gate = check_proactive_availability(
        budget=_quiet_budget(proactive_min_gap_minutes=30),
        mood=_mood(),
        relationship=_relationship(),
        last_user_message_at=(now - timedelta(minutes=10)).isoformat(),
        now=now,
    )
    assert gate.blocked is True
    assert gate.reason == "post_conversation_cooldown"


def test_quiet_hours_block() -> None:
    now = datetime(2026, 6, 13, 2, 0, tzinfo=timezone.utc)
    gate = check_proactive_availability(
        budget=_quiet_budget(proactive_quiet_hours=(23, 8)),
        mood=_mood(),
        relationship=_relationship(),
        last_user_message_at=None,
        now=now,
    )
    assert gate.blocked is True
    assert gate.reason == "quiet_hours"


def test_daily_cap_blocks() -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    gate = check_proactive_availability(
        budget=_quiet_budget(proactive_daily_max=2),
        mood=_mood(proactive_daily_date="2026-06-13", proactive_daily_count=2),
        relationship=_relationship(),
        last_user_message_at=None,
        now=now,
    )
    assert gate.blocked is True
    assert gate.reason == "proactive_daily_cap"


def test_proactive_check_fires_with_high_longing_and_seeded_rng(store: MemoryStore) -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    store.update_relationship_state(
        closeness=0.85,
        last_meaningful_interaction_at=(now - timedelta(hours=30)).isoformat(),
    )
    store.update_mood_state(
        loneliness=0.75,
        metadata={"last_proactive_check_at": (now - timedelta(hours=1)).isoformat()},
    )

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_hot_budget(),
        rng=random.Random(0),
        now=now,
    )
    assert decision.decision == "proactive"
    assert decision.reason == "check_in"


def test_proactive_check_stale_job_when_memory_exists(store: MemoryStore) -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    store.update_relationship_state(
        closeness=0.85,
        last_meaningful_interaction_at=(now - timedelta(hours=30)).isoformat(),
    )
    store.update_mood_state(
        loneliness=0.75,
        metadata={"last_proactive_check_at": (now - timedelta(hours=1)).isoformat()},
    )
    memory = store.create_memory(
        type="job_progress",
        content="Applied to two backend roles.",
        tags=["job-search"],
    )
    with connect(store.db_path) as connection:
        connection.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?",
            ("2020-01-01T00:00:00+00:00", memory.id),
        )

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_hot_budget(),
        rng=random.Random(0),
        now=now,
    )
    assert decision.decision == "proactive"
    assert decision.reason == "commitment_followup"


def test_proactive_check_misses_when_lambda_zero(store: MemoryStore) -> None:
    from datetime import datetime, timezone

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_quiet_budget(proactive_quiet_hours=(0, 0)),
        rng=random.Random(0),
        now=datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc),
    )
    assert decision.decision == "observe"
    assert decision.reason == "longing_poisson_miss"


def _tier_budget(**overrides: object) -> BudgetConfig:
    base = {
        "longing_tier_bored_hours": 24.0,
        "longing_tier_longing_hours": 48.0,
        "longing_tier_sulk_hours": 72.0,
        "longing_tier_sulk_closeness_min": 0.6,
    }
    base.update(overrides)
    return BudgetConfig(**base)


def test_longing_tier_no_interaction_history_is_bored() -> None:
    tier = compute_longing_tier(
        last_meaningful_interaction_at=None,
        closeness=0.9,
        budget=_tier_budget(),
        now=datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc),
    )
    assert tier == "bored"


def test_longing_tier_fresh_interaction_is_bored() -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    tier = compute_longing_tier(
        last_meaningful_interaction_at=(now - timedelta(hours=2)).isoformat(),
        closeness=0.9,
        budget=_tier_budget(),
        now=now,
    )
    assert tier == "bored"


def test_longing_tier_moderate_silence_is_longing() -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    tier = compute_longing_tier(
        last_meaningful_interaction_at=(now - timedelta(hours=50)).isoformat(),
        closeness=0.9,
        budget=_tier_budget(),
        now=now,
    )
    assert tier == "longing"


def test_longing_tier_high_silence_high_closeness_is_sulk() -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    tier = compute_longing_tier(
        last_meaningful_interaction_at=(now - timedelta(hours=100)).isoformat(),
        closeness=0.9,
        budget=_tier_budget(),
        now=now,
    )
    assert tier == "sulk"


def test_longing_tier_high_silence_low_closeness_caps_at_longing() -> None:
    """Sulking requires closeness — distant relationships never reach 'sulk', no matter how long the silence."""
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    tier = compute_longing_tier(
        last_meaningful_interaction_at=(now - timedelta(hours=100)).isoformat(),
        closeness=0.2,
        budget=_tier_budget(),
        now=now,
    )
    assert tier == "longing"
