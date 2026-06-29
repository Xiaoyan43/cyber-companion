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
        "longing_lambda_base_per_hour": 0.0,
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


def test_delta_seconds_preserves_full_absence() -> None:
    now = _now()
    metadata = {"last_proactive_check_at": (now - timedelta(hours=24)).isoformat()}
    snap = snapshot_longing(
        closeness=0.8,
        loneliness=0.7,
        last_meaningful_interaction_at=(now - timedelta(hours=10)).isoformat(),
        metadata=metadata,
        budget=BudgetConfig(longing_lambda_base_per_hour=0.05),
        now=now,
    )
    assert snap.delta_seconds == 24 * 3600.0


def test_delta_seconds_preserves_short_interval() -> None:
    now = _now()
    metadata = {"last_proactive_check_at": (now - timedelta(minutes=5)).isoformat()}
    snap = snapshot_longing(
        closeness=0.8,
        loneliness=0.7,
        last_meaningful_interaction_at=(now - timedelta(hours=10)).isoformat(),
        metadata=metadata,
        budget=BudgetConfig(longing_lambda_base_per_hour=0.05),
        now=now,
    )
    assert snap.delta_seconds == pytest.approx(300.0)


def test_force_proactive_still_respects_enable_proactive(store: MemoryStore) -> None:
    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check", metadata={"force_proactive": True}),
        budget=_quiet_budget(enable_proactive=False),
        now=_now(),
    )
    assert decision.decision == "observe"
    assert decision.reason == "proactive_disabled"


def test_rtc_voice_turn_uses_chat_source(store: MemoryStore) -> None:
    """RTC off-path turns persist via persist_chat_turn → source='chat'."""
    from backend.app.schemas import ChatMessageSchema

    persist_chat_turn(
        store,
        [ChatMessageSchema(role="user", content="语音里说的")],
        _completion_result(),
    )

    store.create_message(role="user", content="tick only", source="behavior_tick")
    messages = store.list_messages(limit=10)
    chat_users = [m for m in messages if m.role == "user" and m.source == "chat"]
    assert chat_users[-1].content == "语音里说的"


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
