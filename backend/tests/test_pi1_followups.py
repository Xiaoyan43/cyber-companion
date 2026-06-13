from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.longing import snapshot_longing
from backend.app.behavior.types import BehaviorEvent
from backend.app.main import app
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.chat_persistence import persist_chat_turn
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.providers.router import reset_provider_router
from backend.app.providers.types import ChatCompletionResult, CostEstimate, TokenUsage


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "pi1_followups.db")


def _now() -> datetime:
    return datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)


def _quiet_budget(**overrides: object) -> BudgetConfig:
    base = {
        "enable_proactive": True,
        "proactive_min_gap_minutes": 30,
        "proactive_min_fire_gap_hours": 6.0,
        "proactive_daily_max": 10,
        "proactive_quiet_hours": (23, 8),
        "longing_lambda_base_per_hour": 0.0,
        "proactive_max_delta_seconds": 600,
    }
    base.update(overrides)
    return BudgetConfig(**base)


def _completion_result() -> ChatCompletionResult:
    usage = TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15)
    cost = CostEstimate(input_usd=0.0, output_usd=0.0, total_usd=0.0, pricing_source="mock")
    return ChatCompletionResult(
        provider="mock",
        model="mock-boxi",
        content="嗯。",
        usage=usage,
        cost=cost,
        mock=True,
    )


def test_delta_seconds_clamped_after_long_absence() -> None:
    now = _now()
    metadata = {"last_proactive_check_at": (now - timedelta(hours=24)).isoformat()}
    snap = snapshot_longing(
        closeness=0.8,
        loneliness=0.7,
        last_meaningful_interaction_at=(now - timedelta(hours=10)).isoformat(),
        metadata=metadata,
        budget=BudgetConfig(proactive_max_delta_seconds=600, longing_lambda_base_per_hour=0.05),
        now=now,
    )
    assert snap.delta_seconds == 600.0


def test_delta_seconds_unchanged_within_cap() -> None:
    now = _now()
    metadata = {"last_proactive_check_at": (now - timedelta(minutes=5)).isoformat()}
    snap = snapshot_longing(
        closeness=0.8,
        loneliness=0.7,
        last_meaningful_interaction_at=(now - timedelta(hours=10)).isoformat(),
        metadata=metadata,
        budget=BudgetConfig(proactive_max_delta_seconds=600, longing_lambda_base_per_hour=0.05),
        now=now,
    )
    assert snap.delta_seconds == pytest.approx(300.0)


def test_force_proactive_skips_timing_gates(store: MemoryStore) -> None:
    now = datetime(2026, 6, 13, 2, 0, tzinfo=timezone.utc)
    store.create_message(role="user", content="刚聊完", source="chat")
    store.update_mood_state(
        metadata={
            "last_proactive_fired_at": (now - timedelta(hours=1)).isoformat(),
            "last_proactive_check_at": (now - timedelta(hours=1)).isoformat(),
        },
    )

    normal = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_quiet_budget(longing_lambda_base_per_hour=80.0),
        rng=random.Random(0),
        now=now,
    )
    assert normal.decision == "observe"
    assert normal.reason in {"quiet_hours", "post_conversation_cooldown", "proactive_fire_gap"}

    forced = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check", metadata={"force_proactive": True}),
        budget=_quiet_budget(longing_lambda_base_per_hour=0.0),
        rng=random.Random(99),
        now=now,
    )
    assert forced.decision == "proactive"


def test_force_proactive_still_respects_backoff(store: MemoryStore) -> None:
    now = _now()
    store.update_mood_state(
        metadata={"proactive_pending_since": (now - timedelta(minutes=5)).isoformat()},
    )
    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check", metadata={"force_proactive": True}),
        budget=_quiet_budget(proactive_quiet_hours=(0, 0), proactive_min_gap_minutes=0),
        now=now,
    )
    assert decision.decision == "observe"
    assert decision.reason == "awaiting_user_reply"


def test_force_proactive_still_respects_enable_proactive(store: MemoryStore) -> None:
    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check", metadata={"force_proactive": True}),
        budget=_quiet_budget(enable_proactive=False, proactive_quiet_hours=(0, 0)),
        now=_now(),
    )
    assert decision.decision == "observe"
    assert decision.reason == "proactive_disabled"


def test_rtc_voice_turn_uses_chat_source_for_cooldown(store: MemoryStore) -> None:
    """RTC off-path turns persist via persist_chat_turn → source='chat'."""
    from backend.app.schemas import ChatMessageSchema

    persist_chat_turn(
        store,
        [ChatMessageSchema(role="user", content="语音里说的")],
        _completion_result(),
    )
    assert store.get_last_user_chat_created_at() is not None

    store.create_message(role="user", content="tick only", source="behavior_tick")
    messages = store.list_messages(limit=10)
    chat_users = [m for m in messages if m.role == "user" and m.source == "chat"]
    assert chat_users[-1].content == "语音里说的"
    assert store.get_last_user_chat_created_at() == chat_users[-1].created_at


@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    reset_provider_router()
    reset_memory_store()
    yield
    reset_provider_router()
    reset_memory_store()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    return TestClient(app)


def test_behavior_evaluate_force_proactive_route(client: TestClient) -> None:
    with patch("backend.app.behavior.engine.should_fire_longing", return_value=False):
        blocked = client.post(
            "/behavior/evaluate",
            json={"event_type": "proactive_check", "force_proactive": False},
        )
    assert blocked.status_code == 200
    assert blocked.json()["decision"] == "observe"

    response = client.post(
        "/behavior/evaluate",
        json={"event_type": "proactive_check", "force_proactive": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "proactive"
    assert body["saved_message_id"] is not None
