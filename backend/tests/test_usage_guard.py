from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory import usage_guard
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.memory.usage_guard import evaluate_llm_budget_gate, is_reasoning_model
from backend.app.providers.router import reset_provider_router

_EPOCH = "2000-01-01 00:00:00"


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "usage.db")


def _llm_turn(store: MemoryStore, *, cost_usd: float = 0.0) -> None:
    store.create_message(
        role="assistant",
        content="reply",
        metadata={"should_call_llm": True, "cost": {"total_usd": cost_usd}},
    )


def test_store_counts_only_llm_turns_and_sums_cost(store: MemoryStore) -> None:
    _llm_turn(store, cost_usd=0.01)
    _llm_turn(store, cost_usd=0.02)
    store.create_message(
        role="assistant",
        content="……",
        source="behavior_tick",
        metadata={"should_call_llm": False, "cost": {"total_usd": 0.0}},
    )

    assert store.count_llm_turns_since(_EPOCH) == 2
    assert store.sum_llm_cost_since(_EPOCH) == pytest.approx(0.03)


def test_gate_allows_when_under_limits(store: MemoryStore) -> None:
    gate = evaluate_llm_budget_gate(store, BudgetConfig(), target_model="deepseek-chat")
    assert gate.allowed is True
    assert gate.block_line is None


def test_gate_blocks_on_daily_turn_limit(store: MemoryStore) -> None:
    _llm_turn(store)
    _llm_turn(store)
    gate = evaluate_llm_budget_gate(
        store,
        BudgetConfig(daily_llm_turn_limit=2),
        target_model="deepseek-chat",
    )
    assert gate.allowed is False
    assert gate.blocked_by == "daily_turns"
    assert gate.block_line


def test_gate_blocks_on_monthly_cost_limit(store: MemoryStore) -> None:
    _llm_turn(store, cost_usd=0.5)
    gate = evaluate_llm_budget_gate(
        store,
        BudgetConfig(monthly_usd_limit=0.1),
        target_model="deepseek-chat",
    )
    assert gate.allowed is False
    assert gate.blocked_by == "monthly_usd"


def test_gate_blocks_reasoning_model_when_disallowed(store: MemoryStore) -> None:
    gate = evaluate_llm_budget_gate(
        store,
        BudgetConfig(allow_reasoning_model=False),
        target_model="deepseek-reasoner",
    )
    assert gate.allowed is False
    assert gate.blocked_by == "reasoning_model"


def test_gate_allows_reasoning_model_when_enabled(store: MemoryStore) -> None:
    gate = evaluate_llm_budget_gate(
        store,
        BudgetConfig(allow_reasoning_model=True),
        target_model="deepseek-reasoner",
    )
    assert gate.allowed is True


def test_is_reasoning_model() -> None:
    assert is_reasoning_model("deepseek-reasoner") is True
    assert is_reasoning_model("o1-mini") is True
    assert is_reasoning_model("deepseek-chat") is False
    assert is_reasoning_model("mock-boxi") is False


def test_zero_limits_disable_caps(store: MemoryStore) -> None:
    for _ in range(5):
        _llm_turn(store, cost_usd=100.0)
    gate = evaluate_llm_budget_gate(
        store,
        BudgetConfig(daily_llm_turn_limit=0, monthly_usd_limit=0.0),
        target_model="deepseek-chat",
    )
    assert gate.allowed is True


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


def test_chat_complete_blocks_when_daily_limit_reached(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.app.main as main_module

    monkeypatch.setattr(
        main_module,
        "load_budget_config",
        lambda: BudgetConfig(daily_llm_turn_limit=1),
    )

    first = client.post("/chat/complete", json={"messages": [{"role": "user", "content": "在吗朋友"}]})
    assert first.status_code == 200
    assert first.json()["should_call_llm"] is True
    assert first.json()["provider"] == "mock"

    second = client.post("/chat/complete", json={"messages": [{"role": "user", "content": "再聊聊"}]})
    assert second.status_code == 200
    body = second.json()
    assert body["should_call_llm"] is False
    assert body["provider"] == "local-budget"
    assert body["cost"]["total_usd"] == 0.0
