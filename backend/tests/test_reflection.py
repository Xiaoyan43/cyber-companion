from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.context_builder import build_provider_context
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.memory.summary_policy import maybe_update_conversation_summary
from backend.app.providers.router import reset_provider_router
from backend.app.providers.types import ChatCompletionResult, CostEstimate, TokenUsage
from backend.app.reflection import jobs as reflection_jobs
from backend.app.reflection.runner import run_reflection_if_due


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    reset_provider_router()
    reset_memory_store()
    yield
    reset_provider_router()
    reset_memory_store()


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "reflection.db")


@pytest.fixture
def budget() -> BudgetConfig:
    return BudgetConfig(
        enable_reflection=True,
        reflection_every_n_turns=3,
        llm_summary=True,
        max_raw_turns=2,
        summary_batch_size=2,
    )


def _canned_complete(payload: dict) -> ChatCompletionResult:
    import json

    return ChatCompletionResult(
        provider="mock",
        model="mock-boxi",
        content=json.dumps(payload, ensure_ascii=False),
        usage=TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        cost=CostEstimate(
            input_usd=0.0,
            output_usd=0.0,
            total_usd=0.0,
            pricing_source="mock",
        ),
        mock=True,
    )


def test_note_llm_turn_increments(store: MemoryStore) -> None:
    assert store.note_llm_turn() == 1
    assert store.note_llm_turn() == 2
    assert store.get_meta("turns_since_reflection") == "2"


def test_claim_reflection_at_threshold_and_single_flight(store: MemoryStore) -> None:
    store.set_meta("turns_since_reflection", "3")
    assert store.claim_reflection(3) is True
    assert store.get_meta("reflecting") == "1"
    assert store.get_meta("turns_since_reflection") == "0"
    assert store.claim_reflection(3) is False

    store.release_reflection()
    assert store.get_meta("reflecting") == "0"
    store.set_meta("turns_since_reflection", "3")
    assert store.claim_reflection(3) is True


def test_run_reflection_not_due_below_threshold(
    store: MemoryStore,
    budget: BudgetConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consolidate = MagicMock()
    monkeypatch.setattr(reflection_jobs, "consolidate_memories", consolidate)

    store.set_meta("turns_since_reflection", "1")
    run_reflection_if_due(store, budget)
    consolidate.assert_not_called()


def test_run_reflection_disabled(
    store: MemoryStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consolidate = MagicMock()
    monkeypatch.setattr(reflection_jobs, "consolidate_memories", consolidate)

    store.set_meta("turns_since_reflection", "10")
    run_reflection_if_due(
        store,
        BudgetConfig(enable_reflection=False, reflection_every_n_turns=3),
    )
    consolidate.assert_not_called()
    assert store.get_meta("reflecting", "0") != "1"


def test_failure_isolation_releases_reflecting_flag(
    store: MemoryStore,
    budget: BudgetConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_store: MemoryStore, _budget: BudgetConfig) -> None:
        raise RuntimeError("job failed")

    def ok(_store: MemoryStore, _budget: BudgetConfig) -> None:
        ok.called = True  # type: ignore[attr-defined]

    ok.called = False  # type: ignore[attr-defined]

    monkeypatch.setattr(reflection_jobs, "consolidate_memories", boom)
    monkeypatch.setattr(reflection_jobs, "form_impression", ok)
    monkeypatch.setattr(reflection_jobs, "summarize_conversation_llm", ok)

    store.set_meta("turns_since_reflection", "3")
    run_reflection_if_due(store, budget)

    assert ok.called is True  # type: ignore[attr-defined]
    assert store.get_meta("reflecting") == "0"
    store.set_meta("turns_since_reflection", "3")
    assert store.claim_reflection(3) is True
    store.release_reflection()


def test_form_impression_creates_and_updates_in_place(
    store: MemoryStore,
    budget: BudgetConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        {"impression": "First take: sharp but tired."},
        {"impression": "Updated: still sharp, slightly warmer."},
    ]

    def fake_llm(**_kwargs: object) -> dict | None:
        return responses.pop(0)

    monkeypatch.setattr(reflection_jobs, "_llm_json", fake_llm)

    form_impression = reflection_jobs.form_impression
    form_impression(store, budget)
    memories = store.list_memories(type="relationship_state", limit=5)
    assert len(memories) == 1
    assert memories[0].content == "First take: sharp but tired."
    assert memories[0].metadata.get("writer") == "reflection"

    form_impression(store, budget)
    memories = store.list_memories(type="relationship_state", limit=5)
    assert len(memories) == 1
    assert memories[0].content == "Updated: still sharp, slightly warmer."

    built = build_provider_context(store, user_input="hello")
    assert "[Impression]" in built.messages[0].content
    assert "slightly warmer" in built.messages[0].content


def test_consolidate_archive_and_deprioritize(
    store: MemoryStore,
    budget: BudgetConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale = store.create_memory(
        type="job_progress",
        content="Old application",
        importance=0.7,
    )
    active = store.create_memory(
        type="stable_profile",
        content="Backend engineer",
        importance=0.8,
    )
    unknown_id = 99999

    monkeypatch.setattr(
        reflection_jobs,
        "_llm_json",
        lambda **_kwargs: {
            "archive": [stale.id, unknown_id],
            "deprioritize": [
                {"id": active.id, "importance": 0.1},
                {"id": active.id, "importance": 0.95},
            ],
        },
    )

    reflection_jobs.consolidate_memories(store, budget)

    updated_stale = store.get_memory(stale.id)
    assert updated_stale is not None
    assert updated_stale.expires_at is not None

    updated_active = store.get_memory(active.id)
    assert updated_active is not None
    assert updated_active.importance == pytest.approx(0.1)
    assert updated_active.expires_at is None


def test_maybe_update_summary_defers_when_llm_summary_on(store: MemoryStore) -> None:
    for index in range(8):
        store.create_message(role="user" if index % 2 == 0 else "assistant", content=f"m{index}")

    assert maybe_update_conversation_summary(
        store,
        budget=BudgetConfig(llm_summary=True, max_raw_turns=2, summary_batch_size=2),
    ) is False
    assert store.get_latest_conversation_summary() is None


def test_maybe_update_summary_rule_based_when_llm_summary_off(store: MemoryStore) -> None:
    for index in range(8):
        store.create_message(role="user" if index % 2 == 0 else "assistant", content=f"m{index}")

    assert maybe_update_conversation_summary(
        store,
        budget=BudgetConfig(llm_summary=False, max_raw_turns=2, summary_batch_size=2),
    ) is True
    summary = store.get_latest_conversation_summary()
    assert summary is not None
    assert "Earlier conversation recap" in summary.summary


def test_summarize_job_writes_summary(
    store: MemoryStore,
    budget: BudgetConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for index in range(8):
        store.create_message(role="user" if index % 2 == 0 else "assistant", content=f"line {index}")

    monkeypatch.setattr(
        reflection_jobs,
        "_llm_json",
        lambda **_kwargs: {"summary": "They talked about work.", "keywords": ["work"]},
    )

    reflection_jobs.summarize_conversation_llm(store, budget)
    summary = store.get_latest_conversation_summary()
    assert summary is not None
    assert summary.summary == "They talked about work."
    assert "work" in summary.keywords


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    return TestClient(app)


def test_chat_complete_unaffected_when_reflection_job_raises(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.app.main as main_module

    def boom(_store: MemoryStore, _budget: BudgetConfig) -> None:
        raise RuntimeError("reflection job exploded")

    monkeypatch.setattr(reflection_jobs, "consolidate_memories", boom)
    monkeypatch.setattr(
        main_module,
        "load_budget_config",
        lambda: BudgetConfig(
            enable_reflection=True,
            reflection_every_n_turns=1,
            daily_llm_turn_limit=0,
            monthly_usd_limit=0.0,
        ),
    )

    response = client.post(
        "/chat/complete",
        json={"messages": [{"role": "user", "content": "你好"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["should_call_llm"] is True
    assert body["content"]
