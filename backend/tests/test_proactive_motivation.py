from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.longing import should_fire_longing, snapshot_longing
from backend.app.behavior.motivation import resolve_proactive_motivation
from backend.app.behavior.proactive_reason import pick_agenda_proactive_reason
from backend.app.behavior.types import BehaviorEvent
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "proactive_motivation.db")


def _now() -> datetime:
    return datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc)


def _hot_budget(**overrides: object) -> BudgetConfig:
    base = {
        "enable_proactive": True,
        "proactive_min_gap_minutes": 0,
        "proactive_min_fire_gap_hours": 0.0,
        "proactive_daily_max": 10,
        "proactive_quiet_hours": (0, 0),
        "longing_silence_hours_scale": 24.0,
        "longing_closeness_weight": 0.6,
        "longing_loneliness_weight": 0.4,
        "longing_lambda_base_per_hour": 80.0,
        "longing_lambda_longing_gain": 2.0,
        "proactive_reason_mode": "agenda",
    }
    base.update(overrides)
    return BudgetConfig(**base)


def _prime_longing(store: MemoryStore, now: datetime) -> None:
    store.update_relationship_state(
        closeness=0.85,
        last_meaningful_interaction_at=(now - timedelta(hours=30)).isoformat(),
    )
    store.update_mood_state(
        loneliness=0.75,
        metadata={"last_proactive_check_at": (now - timedelta(hours=1)).isoformat()},
    )


def _longing_snapshot(store: MemoryStore, budget: BudgetConfig, now: datetime):
    mood = store.get_mood_state()
    relationship = store.get_relationship_state()
    return snapshot_longing(
        closeness=relationship.closeness,
        loneliness=mood.loneliness,
        last_meaningful_interaction_at=relationship.last_meaningful_interaction_at,
        metadata=mood.metadata,
        budget=budget,
        now=now,
    )


def test_agenda_mode_blocks_longing_only_check_in(store: MemoryStore) -> None:
    now = _now()
    _prime_longing(store, now)
    budget = _hot_budget()

    motivation = resolve_proactive_motivation(
        store,
        budget=budget,
        longing=_longing_snapshot(store, budget, now),
        longing_tier="longing",
        now=now,
    )
    assert motivation.reason is None
    assert motivation.mode == "agenda"

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=budget,
        rng=random.Random(0),
        now=now,
    )
    assert decision.decision == "observe"
    assert decision.reason == "no_agenda_reason"


def test_agenda_mode_fires_due_open_loop_after_poisson(store: MemoryStore) -> None:
    now = _now()
    _prime_longing(store, now)
    store.create_open_loop(
        kind="follow_up",
        title="收尾报税",
        summary="补交材料",
        due_at=(now - timedelta(hours=1)).isoformat(),
    )

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_hot_budget(),
        rng=random.Random(0),
        now=now,
    )
    assert decision.decision == "proactive"
    assert decision.reason == "open_loop"
    assert decision.proactive_reason is not None
    assert decision.proactive_reason.open_loop_id is not None


def test_agenda_mode_poisson_miss_with_due_loop(store: MemoryStore) -> None:
    now = _now()
    _prime_longing(store, now)
    store.create_open_loop(
        kind="follow_up",
        title="收尾报税",
        due_at=(now - timedelta(hours=1)).isoformat(),
    )
    budget = _hot_budget(longing_lambda_base_per_hour=0.0)

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=budget,
        rng=random.Random(0),
        now=now,
    )
    assert decision.decision == "observe"
    assert decision.reason == "longing_poisson_miss"


def test_longing_only_mode_restores_check_in_fallback(store: MemoryStore) -> None:
    now = _now()
    _prime_longing(store, now)
    budget = _hot_budget(proactive_reason_mode="longing_only")

    motivation = resolve_proactive_motivation(
        store,
        budget=budget,
        longing=_longing_snapshot(store, budget, now),
        longing_tier="longing",
        now=now,
    )
    assert motivation.reason is not None
    assert motivation.reason.kind == "check_in"

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=budget,
        rng=random.Random(0),
        now=now,
    )
    assert decision.decision == "proactive"
    assert decision.reason == "check_in"


def test_force_proactive_uses_check_in_when_agenda_empty(store: MemoryStore) -> None:
    now = _now()
    budget = _hot_budget(longing_lambda_base_per_hour=0.0)

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check", metadata={"force_proactive": True}),
        budget=budget,
        rng=random.Random(99),
        now=now,
    )
    assert decision.decision == "proactive"
    assert decision.reason == "check_in"


def test_open_but_not_due_loop_excluded_from_agenda_reason(store: MemoryStore) -> None:
    now = _now()
    store.create_open_loop(
        kind="future_event",
        title="下月旅行",
        due_at=(now + timedelta(days=30)).isoformat(),
    )
    store.create_open_loop(kind="user_goal", title="学日语")

    assert pick_agenda_proactive_reason(store, now=now) is None


def test_poisson_gate_is_separate_from_reason_selection() -> None:
    """Rhythm gate can pass while agenda is empty — reason step blocks first."""
    budget = _hot_budget(longing_lambda_base_per_hour=80.0)
    longing = snapshot_longing(
        closeness=0.85,
        loneliness=0.75,
        last_meaningful_interaction_at=(datetime(2026, 6, 26, 6, 0, tzinfo=timezone.utc)).isoformat(),
        metadata={"last_proactive_check_at": (datetime(2026, 6, 27, 11, 0, tzinfo=timezone.utc)).isoformat()},
        budget=budget,
        now=_now(),
    )
    assert should_fire_longing(longing, rng=random.Random(0)) is True
