from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.app.behavior.proactive_opener import resolve_proactive_opener
from backend.app.behavior.proactive_reason import ProactiveReason, fallback_line_for_reason
from backend.app.behavior.types import BehaviorDecision
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.chat_persistence import persist_local_behavior_line
from backend.app.memory.store import MemoryStore
from backend.app.providers.router import ProviderRouter


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "pi4.db")


def _now() -> datetime:
    return datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)


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


def test_resolve_proactive_opener_falls_back_on_budget_block(store: MemoryStore) -> None:
    store.create_message(
        role="assistant",
        content="prior",
        metadata={"should_call_llm": True, "cost": {"total_usd": 1.0}},
    )
    router = ProviderRouter.from_config()
    budget = BudgetConfig(
        proactive_llm=True,
        monthly_usd_limit=0.5,
    )
    resolved = resolve_proactive_opener(
        store,
        _proactive_decision(),
        budget=budget,
        router=router,
        provider_name="mock",
        now=_now(),
    )
    assert resolved.proactive_llm_used is False
    assert resolved.local_response == fallback_line_for_reason(resolved.proactive_reason)  # type: ignore[arg-type]


def test_proactive_llm_usage_is_recorded(store: MemoryStore) -> None:
    router = ProviderRouter.from_config()
    budget = BudgetConfig(proactive_llm=True)
    resolved = resolve_proactive_opener(
        store,
        _proactive_decision(),
        budget=budget,
        router=router,
        provider_name="mock",
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
