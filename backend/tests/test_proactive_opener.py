from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.app.behavior.proactive_opener import (
    build_proactive_messages,
    proactive_llm_allowed,
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


@pytest.mark.parametrize("tier", ["bored", "longing", "sulk"])
@pytest.mark.parametrize(
    "kind",
    ["due_reminder", "commitment_followup", "memory_callback", "check_in"],
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
        ("commitment_followup", "commitment"),
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
