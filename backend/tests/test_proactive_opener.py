from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.app.behavior.proactive_opener import (
    build_proactive_messages,
    is_repeated_fingerprint,
    proactive_llm_allowed,
    record_proactive_fingerprint,
    resolve_proactive_opener,
)
from backend.app.behavior.proactive_reason import (
    ProactiveReason,
    fallback_line_for_reason,
    format_reason_block,
    pick_proactive_reason,
)
from backend.app.behavior.types import BehaviorDecision
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MoodStateRecord
from backend.app.memory.store import MemoryStore
from backend.app.providers.router import ProviderRouter


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "proactive_opener.db")


def _now() -> datetime:
    return datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)


def _decision(reason: ProactiveReason) -> BehaviorDecision:
    return BehaviorDecision(
        decision="proactive",
        avatar_state=reason.avatar_state,
        should_call_llm=True,
        reason=reason.kind,
        local_response=fallback_line_for_reason(reason),
        proactive_reason=reason,
    )


def test_reason_picker_prefers_due_reminder(store: MemoryStore) -> None:
    store.create_reminder(
        title="周四面试",
        details="别迟到",
        due_at=(_now() - timedelta(hours=1)).isoformat(),
    )
    store.create_memory(
        type="job_progress",
        content="Applied to roles.",
        importance=0.9,
    )
    reason = pick_proactive_reason(store, longing_intensity=0.8, now=_now())
    assert reason.kind == "due_reminder"
    assert reason.summary == "周四面试"


def test_reason_picker_commitment_before_callback(store: MemoryStore) -> None:
    memory = store.create_memory(
        type="job_progress",
        content="Applied to two backend roles.",
        tags=["job-search"],
        importance=0.8,
    )
    from backend.app.memory.database import connect

    with connect(store.db_path) as connection:
        connection.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?",
            ("2020-01-01T00:00:00+00:00", memory.id),
        )
    store.create_memory(type="stable_profile", content="User likes cats.", importance=0.9)

    reason = pick_proactive_reason(store, now=_now())
    assert reason.kind == "commitment_followup"


def test_reason_picker_memory_callback(store: MemoryStore) -> None:
    store.create_memory(type="stable_profile", content="User plans a NZ trip.", importance=0.85)
    reason = pick_proactive_reason(store, longing_intensity=0.6, now=_now())
    assert reason.kind == "memory_callback"


def test_reason_picker_check_in_fallback(store: MemoryStore) -> None:
    reason = pick_proactive_reason(store, longing_intensity=0.72, now=_now())
    assert reason.kind == "check_in"


def test_reason_picker_propagates_longing_tier_to_due_reminder(store: MemoryStore) -> None:
    """Longing tier is orthogonal to intent — even a due-reminder reason carries it."""
    store.create_reminder(
        title="周四面试",
        details="别迟到",
        due_at=(_now() - timedelta(hours=1)).isoformat(),
    )
    reason = pick_proactive_reason(store, longing_tier="sulk", now=_now())
    assert reason.kind == "due_reminder"
    assert reason.longing_tier == "sulk"


def test_reason_picker_default_tier_is_bored(store: MemoryStore) -> None:
    reason = pick_proactive_reason(store, longing_intensity=0.1, now=_now())
    assert reason.longing_tier == "bored"


def test_reason_picker_open_loop_when_due(store: MemoryStore) -> None:
    store.create_open_loop(
        kind="follow_up",
        title="收尾报税",
        summary="补交材料",
        due_at=(_now() - timedelta(hours=1)).isoformat(),
    )
    reason = pick_proactive_reason(store, now=_now())
    assert reason.kind == "open_loop"
    assert reason.summary == "收尾报税"
    assert reason.detail == "补交材料"
    assert reason.open_loop_id is not None


def test_reason_picker_due_reminder_beats_open_loop(store: MemoryStore) -> None:
    store.create_reminder(
        title="周四面试",
        due_at=(_now() - timedelta(hours=1)).isoformat(),
    )
    store.create_open_loop(
        kind="follow_up",
        title="收尾报税",
        due_at=(_now() - timedelta(hours=2)).isoformat(),
    )
    reason = pick_proactive_reason(store, now=_now())
    assert reason.kind == "due_reminder"


def test_reason_picker_open_loop_beats_commitment(store: MemoryStore) -> None:
    memory = store.create_memory(
        type="job_progress",
        content="Applied to two backend roles.",
        importance=0.8,
    )
    from backend.app.memory.database import connect

    with connect(store.db_path) as connection:
        connection.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?",
            ("2020-01-01T00:00:00+00:00", memory.id),
        )
    store.create_open_loop(
        kind="commitment",
        title="还书",
        due_at=(_now() - timedelta(hours=1)).isoformat(),
    )
    reason = pick_proactive_reason(store, now=_now())
    assert reason.kind == "open_loop"


def test_reason_picker_open_loop_not_due_does_not_trigger(store: MemoryStore) -> None:
    store.create_open_loop(kind="user_goal", title="学日语")  # no due_at
    store.create_open_loop(
        kind="future_event",
        title="下月旅行",
        due_at=(_now() + timedelta(days=30)).isoformat(),
    )
    reason = pick_proactive_reason(store, longing_intensity=0.5, now=_now())
    assert reason.kind == "check_in"


def test_open_loop_reason_carries_longing_tier(store: MemoryStore) -> None:
    store.create_open_loop(
        kind="follow_up",
        title="收尾报税",
        due_at=(_now() - timedelta(hours=1)).isoformat(),
    )
    reason = pick_proactive_reason(store, longing_tier="sulk", now=_now())
    assert reason.kind == "open_loop"
    assert reason.longing_tier == "sulk"


def test_fallback_line_for_open_loop_mentions_title() -> None:
    reason = ProactiveReason(
        kind="open_loop",
        avatar_state="worried",
        summary="报税",
        detail="补交材料",
    )
    line = fallback_line_for_reason(reason)
    assert "报税" in line


@pytest.mark.parametrize("tier", ["bored", "longing", "sulk"])
@pytest.mark.parametrize(
    "kind",
    ["due_reminder", "open_loop", "commitment_followup", "share", "memory_callback", "check_in"],
)
def test_format_reason_block_includes_tier_voice_for_every_kind(kind: str, tier: str) -> None:
    reason = ProactiveReason(
        kind=kind,  # type: ignore[arg-type]
        avatar_state="worried",
        summary="test",
        detail="detail line",
        longing_tier=tier,  # type: ignore[arg-type]
    )
    block = format_reason_block(reason)
    assert f"Longing tier: {tier}" in block
    if tier == "sulk":
        assert "indifference" in block.lower() or "withdrawal" in block.lower()


@pytest.mark.parametrize(
    ("kind", "needle"),
    [
        ("due_reminder", "due reminder"),
        ("open_loop", "open loop"),
        ("commitment_followup", "commitment"),
        ("share", "share"),
        ("memory_callback", "memory callback"),
        ("check_in", "check-in"),
    ],
)
def test_build_proactive_messages_includes_reason_block(
    store: MemoryStore,
    kind: str,
    needle: str,
) -> None:
    reason = ProactiveReason(
        kind=kind,  # type: ignore[arg-type]
        avatar_state="worried",
        summary="test",
        detail="detail line",
        longing_intensity=0.5,
    )
    messages = build_proactive_messages(store, reason)
    system = messages[0].content.lower()
    assert needle in system
    assert "relationship" in system or "trust=" in system


def test_proactive_llm_gate_respects_daily_cap() -> None:
    mood = MoodStateRecord(
        updated_at="2026-06-13T12:00:00+00:00",
        mood="idle",
        energy=0.5,
        annoyance=0.1,
        boredom=0.2,
        worry=0.1,
        trust=0.5,
        loneliness=0.3,
        metadata={"proactive_llm_daily_date": "2026-06-13", "proactive_llm_daily_count": 5},
    )
    budget = BudgetConfig(proactive_llm=True, proactive_llm_daily_max=5)
    assert proactive_llm_allowed(budget, mood, now=_now()) is False


def test_record_proactive_fingerprint_rolls_fifo_at_cap() -> None:
    reasons = [
        ProactiveReason(kind="check_in", avatar_state="worried", summary="s", detail="d", longing_tier=tier)
        for tier in ["bored", "longing", "sulk", "bored", "longing"]
    ]
    metadata: dict[str, object] = {}
    for reason in reasons:
        metadata = record_proactive_fingerprint(metadata, reason, max_size=3)
    assert metadata["proactive_recent_fingerprints"] == [
        "check_in:sulk",
        "check_in:bored",
        "check_in:longing",
    ]


def test_is_repeated_fingerprint_detects_same_kind_and_tier() -> None:
    first = ProactiveReason(
        kind="memory_callback", avatar_state="idle", summary="s", detail="d", longing_tier="longing"
    )
    metadata = record_proactive_fingerprint({}, first, max_size=4)

    same = ProactiveReason(
        kind="memory_callback", avatar_state="idle", summary="s2", detail="d2", longing_tier="longing"
    )
    different_tier = ProactiveReason(
        kind="memory_callback", avatar_state="idle", summary="s3", detail="d3", longing_tier="sulk"
    )
    assert is_repeated_fingerprint(metadata, same) is True
    assert is_repeated_fingerprint(metadata, different_tier) is False


def test_is_repeated_fingerprint_false_when_no_history() -> None:
    reason = ProactiveReason(kind="check_in", avatar_state="worried", summary="s", detail="d")
    assert is_repeated_fingerprint({}, reason) is False


def test_resolve_proactive_opener_records_fingerprint_on_success(store: MemoryStore) -> None:
    reason = ProactiveReason(
        kind="check_in",
        avatar_state="worried",
        summary="check-in",
        detail="longing=0.8",
        longing_intensity=0.8,
        longing_tier="sulk",
    )
    router = ProviderRouter.from_config()
    budget = BudgetConfig(proactive_llm=True, proactive_llm_daily_max=5)

    resolved = resolve_proactive_opener(
        store,
        _decision(reason),
        budget=budget,
        router=router,
        now=_now(),
    )
    assert resolved.proactive_llm_used is True
    mood = store.get_mood_state()
    assert mood.metadata.get("proactive_recent_fingerprints") == ["check_in:sulk"]


def test_resolve_proactive_opener_uses_mock_line(store: MemoryStore) -> None:
    reason = ProactiveReason(
        kind="check_in",
        avatar_state="worried",
        summary="check-in",
        detail="longing=0.8",
        longing_intensity=0.8,
    )
    router = ProviderRouter.from_config()
    budget = BudgetConfig(proactive_llm=True, proactive_llm_daily_max=5)

    resolved = resolve_proactive_opener(
        store,
        _decision(reason),
        budget=budget,
        router=router,
        now=_now(),
    )
    assert resolved.proactive_llm_used is True
    assert resolved.local_response
    assert resolved.local_response != fallback_line_for_reason(reason)


def test_resolve_proactive_opener_falls_back_when_llm_disabled(store: MemoryStore) -> None:
    reason = pick_proactive_reason(store, longing_intensity=0.5, now=_now())
    router = ProviderRouter.from_config()
    budget = BudgetConfig(proactive_llm=False)

    resolved = resolve_proactive_opener(
        store,
        _decision(reason),
        budget=budget,
        router=router,
        now=_now(),
    )
    assert resolved.proactive_llm_used is False
    assert resolved.local_response == fallback_line_for_reason(reason)


def test_resolve_proactive_opener_falls_back_on_provider_failure(store: MemoryStore) -> None:
    reason = pick_proactive_reason(store, longing_intensity=0.5, now=_now())
    router = MagicMock()
    router.complete.side_effect = RuntimeError("provider down")
    budget = BudgetConfig(proactive_llm=True)

    resolved = resolve_proactive_opener(
        store,
        _decision(reason),
        budget=budget,
        router=router,
        now=_now(),
    )
    assert resolved.proactive_llm_used is False
    assert resolved.local_response == fallback_line_for_reason(reason)


def test_rate_limit_hook_blocks_second_llm_call(store: MemoryStore) -> None:
    reason = ProactiveReason(
        kind="check_in",
        avatar_state="worried",
        summary="check-in",
        detail="longing=0.8",
        longing_intensity=0.8,
    )
    router = ProviderRouter.from_config()
    budget = BudgetConfig(proactive_llm=True, proactive_llm_daily_max=1)

    first = resolve_proactive_opener(
        store,
        _decision(reason),
        budget=budget,
        router=router,
        now=_now(),
    )
    assert first.proactive_llm_used is True

    second = resolve_proactive_opener(
        store,
        _decision(reason),
        budget=budget,
        router=router,
        now=_now(),
    )
    assert second.proactive_llm_used is False
    assert second.local_response == fallback_line_for_reason(reason)
