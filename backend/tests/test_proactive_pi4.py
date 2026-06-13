from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.longing import (
    check_proactive_availability,
    clear_proactive_pending,
    mark_proactive_fired,
)
from backend.app.behavior.proactive_opener import resolve_proactive_opener
from backend.app.behavior.proactive_reason import ProactiveReason, fallback_line_for_reason
from backend.app.behavior.types import BehaviorDecision, BehaviorEvent
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.chat_persistence import persist_local_behavior_line
from backend.app.memory.database import MoodStateRecord, RelationshipStateRecord
from backend.app.memory.store import MemoryStore
from backend.app.providers.router import ProviderRouter


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "pi4.db")


def _now() -> datetime:
    return datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)


def _quiet_budget(**overrides: object) -> BudgetConfig:
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
    }
    base.update(overrides)
    return BudgetConfig(**base)


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


def _relationship() -> RelationshipStateRecord:
    return RelationshipStateRecord(
        updated_at="2026-06-13T12:00:00+00:00",
        trust=0.5,
        closeness=0.2,
        familiarity=0.0,
        tension=0.0,
        last_meaningful_interaction_at=None,
        metadata={},
    )


def _proactive_decision() -> BehaviorDecision:
    reason = ProactiveReason(
        kind="check_in",
        avatar_state="worried",
        summary="check-in",
        detail="longing=0.8",
        longing_intensity=0.8,
    )
    return BehaviorDecision(
        decision="proactive",
        avatar_state=reason.avatar_state,
        should_call_llm=True,
        reason=reason.kind,
        local_response=fallback_line_for_reason(reason),
        proactive_reason=reason,
    )


def test_awaiting_user_reply_blocks() -> None:
    now = _now()
    gate = check_proactive_availability(
        budget=_quiet_budget(),
        mood=_mood(proactive_pending_since=(now - timedelta(minutes=30)).isoformat()),
        relationship=_relationship(),
        last_user_message_at=None,
        now=now,
    )
    assert gate.blocked is True
    assert gate.reason == "awaiting_user_reply"


def test_fire_gap_blocks_within_hours() -> None:
    now = _now()
    gate = check_proactive_availability(
        budget=_quiet_budget(proactive_min_fire_gap_hours=6.0),
        mood=_mood(last_proactive_fired_at=(now - timedelta(hours=2)).isoformat()),
        relationship=_relationship(),
        last_user_message_at=None,
        now=now,
    )
    assert gate.blocked is True
    assert gate.reason == "proactive_fire_gap"


def test_fire_gap_allows_after_hours() -> None:
    now = _now()
    gate = check_proactive_availability(
        budget=_quiet_budget(proactive_min_fire_gap_hours=6.0),
        mood=_mood(last_proactive_fired_at=(now - timedelta(hours=7)).isoformat()),
        relationship=_relationship(),
        last_user_message_at=None,
        now=now,
    )
    assert gate.blocked is False


def test_mark_proactive_fired_sets_pending_and_last_fired() -> None:
    now = _now()
    updated = mark_proactive_fired({}, now=now)
    assert updated["proactive_pending_since"]
    assert updated["last_proactive_fired_at"] == updated["proactive_pending_since"]


def test_clear_proactive_pending_removes_marker() -> None:
    cleared = clear_proactive_pending({"proactive_pending_since": "2026-06-13T12:00:00+00:00"})
    assert "proactive_pending_since" not in cleared


def test_proactive_check_blocked_while_awaiting_reply(store: MemoryStore) -> None:
    now = _now()
    store.update_mood_state(
        metadata={
            "proactive_pending_since": (now - timedelta(minutes=10)).isoformat(),
            "last_proactive_check_at": (now - timedelta(hours=1)).isoformat(),
        },
    )
    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_quiet_budget(),
        rng=random.Random(0),
        now=now,
    )
    assert decision.decision == "observe"
    assert decision.reason == "awaiting_user_reply"


def test_user_message_clears_pending_and_unblocks(store: MemoryStore) -> None:
    now = _now()
    store.update_mood_state(
        metadata={
            "proactive_pending_since": (now - timedelta(minutes=10)).isoformat(),
            "last_proactive_check_at": (now - timedelta(hours=1)).isoformat(),
        },
    )
    evaluate_behavior(
        store,
        BehaviorEvent(event_type="user_message", user_input="在吗"),
    )
    mood = store.get_mood_state()
    assert "proactive_pending_since" not in mood.metadata

    store.update_relationship_state(
        closeness=0.85,
        last_meaningful_interaction_at=(now - timedelta(hours=30)).isoformat(),
    )
    store.update_mood_state(
        loneliness=0.75,
        metadata={
            **mood.metadata,
            "last_proactive_check_at": (now - timedelta(hours=1)).isoformat(),
        },
    )
    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_quiet_budget(),
        rng=random.Random(0),
        now=now,
    )
    assert decision.decision == "proactive"


def test_resolve_proactive_opener_falls_back_on_budget_block(store: MemoryStore) -> None:
    store.create_message(
        role="assistant",
        content="prior",
        metadata={"should_call_llm": True, "cost": {"total_usd": 1.0}},
    )
    router = ProviderRouter.from_config()
    budget = BudgetConfig(
        proactive_llm=True,
        proactive_llm_daily_max=5,
        monthly_usd_limit=0.5,
    )
    resolved = resolve_proactive_opener(
        store,
        _proactive_decision(),
        budget=budget,
        router=router,
        now=_now(),
    )
    assert resolved.proactive_llm_used is False
    assert resolved.local_response == fallback_line_for_reason(resolved.proactive_reason)  # type: ignore[arg-type]


def test_proactive_llm_usage_is_recorded(store: MemoryStore) -> None:
    router = ProviderRouter.from_config()
    budget = BudgetConfig(proactive_llm=True, proactive_llm_daily_max=5)
    resolved = resolve_proactive_opener(
        store,
        _proactive_decision(),
        budget=budget,
        router=router,
        now=_now(),
    )
    assert resolved.proactive_llm_used is True
    assert resolved.proactive_completion is not None

    message_id = persist_local_behavior_line(
        store,
        resolved,
        event_type="proactive_check",
    )
    messages = store.list_messages(limit=5)
    message = next(item for item in messages if item.id == message_id)
    assert message.metadata["should_call_llm"] is True
    assert message.metadata["proactive_llm"] is True
    assert message.metadata["cost"]["total_usd"] >= 0.0

    assert store.count_llm_turns_since("2000-01-01 00:00:00") == 1
    assert store.sum_llm_cost_since("2000-01-01 00:00:00") >= 0.0
