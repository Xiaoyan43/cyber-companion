from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.app.behavior.proactive_opener import resolve_proactive_opener
from backend.app.behavior.proactive_reason import (
    ProactiveReason,
    fallback_line_for_reason,
    is_share_repeated,
    pick_proactive_reason,
    record_share_fingerprint,
)
from backend.app.behavior.types import BehaviorDecision
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore
from backend.app.providers.router import ProviderRouter


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "proactive_share.db")


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


def test_reason_picker_picks_share_when_no_higher_priority_intent(store: MemoryStore) -> None:
    memory = store.create_memory(type="idle_experience", content="刚刚瞎想了一部老电影。")
    reason = pick_proactive_reason(store, now=_now())
    assert reason.kind == "share"
    assert reason.memory_id == memory.id
    assert reason.detail == "刚刚瞎想了一部老电影。"


def test_reason_picker_commitment_before_share(store: MemoryStore) -> None:
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
    store.create_memory(type="idle_experience", content="刚刚瞎想了一部老电影。")

    reason = pick_proactive_reason(store, now=_now())
    assert reason.kind == "commitment_followup"


def test_reason_picker_skips_share_when_all_recently_used(store: MemoryStore) -> None:
    memory = store.create_memory(type="idle_experience", content="刚刚瞎想了一部老电影。")
    metadata = record_share_fingerprint({}, memory.id, max_size=4)
    store.update_mood_state(metadata=metadata)

    reason = pick_proactive_reason(store, now=_now())
    assert reason.kind == "check_in"


def test_reason_picker_falls_back_to_callback_when_share_pool_empty(store: MemoryStore) -> None:
    store.create_memory(type="stable_profile", content="User plans a NZ trip.", importance=0.85)
    reason = pick_proactive_reason(store, now=_now())
    assert reason.kind == "memory_callback"


def test_is_share_repeated_detects_used_memory_id() -> None:
    metadata = record_share_fingerprint({}, 7, max_size=4)
    assert is_share_repeated(metadata, 7) is True
    assert is_share_repeated(metadata, 8) is False


def test_record_share_fingerprint_rolls_fifo_at_cap() -> None:
    metadata: dict[str, object] = {}
    for memory_id in [1, 2, 3, 4, 5]:
        metadata = record_share_fingerprint(metadata, memory_id, max_size=3)
    assert metadata["share_recent_memory_ids"] == [3, 4, 5]


def test_resolve_proactive_opener_records_share_fingerprint_on_success(store: MemoryStore) -> None:
    memory = store.create_memory(type="idle_experience", content="刚刚瞎想了一部老电影。")
    reason = ProactiveReason(
        kind="share",
        avatar_state="happy",
        summary="想分享的小事",
        detail=memory.content,
        memory_id=memory.id,
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
    assert mood.metadata.get("share_recent_memory_ids") == [memory.id]


def test_resolve_proactive_opener_skips_share_fingerprint_on_llm_failure(store: MemoryStore) -> None:
    memory = store.create_memory(type="idle_experience", content="刚刚瞎想了一部老电影。")
    reason = ProactiveReason(
        kind="share",
        avatar_state="happy",
        summary="想分享的小事",
        detail=memory.content,
        memory_id=memory.id,
    )
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
    mood = store.get_mood_state()
    assert mood.metadata.get("share_recent_memory_ids") is None
