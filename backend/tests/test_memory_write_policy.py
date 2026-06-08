from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.memory.write_policy import maybe_write_memories_from_turn
from backend.app.providers.router import reset_provider_router


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    reset_provider_router()
    reset_memory_store()
    yield
    reset_provider_router()
    reset_memory_store()


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "write-policy.db")


def test_explicit_remember_writes_reminder(store: MemoryStore) -> None:
    user_message = store.create_message(role="user", content="记住下周三投递简历")

    written = maybe_write_memories_from_turn(
        store,
        user_input="记住下周三投递简历",
        source_message_id=user_message.id,
    )

    assert len(written) == 1
    assert written[0].type == "reminder"
    assert "下周三投递简历" in written[0].content
    assert written[0].source_message_id == user_message.id
    assert written[0].confidence >= 0.8


def test_job_progress_requires_action_not_bare_keyword(store: MemoryStore) -> None:
    assert maybe_write_memories_from_turn(
        store,
        user_input="我在看求职信息",
        source_message_id=None,
    ) == []

    written = maybe_write_memories_from_turn(
        store,
        user_input="我今天投递了两份后端简历",
        source_message_id=None,
    )
    assert len(written) == 1
    assert written[0].type == "job_progress"


def test_low_value_input_writes_nothing(store: MemoryStore) -> None:
    assert maybe_write_memories_from_turn(store, user_input="嗯", source_message_id=None) == []


def test_similar_memory_updates_instead_of_duplicating(store: MemoryStore) -> None:
    store.create_memory(
        type="job_progress",
        content="我今天投递了两份后端简历",
        tags=["job-search"],
        importance=0.6,
        confidence=0.65,
    )

    written = maybe_write_memories_from_turn(
        store,
        user_input="我今天投递了两份后端简历，还约了周四面试",
        source_message_id=None,
    )

    assert len(written) == 1
    assert store.list_memories(type="job_progress", limit=10) == [written[0]]
    assert "周四面试" in written[0].content
    assert written[0].confidence >= 0.65


def test_auto_memory_write_can_be_disabled(store: MemoryStore) -> None:
    budget = BudgetConfig(auto_memory_write=False)

    assert maybe_write_memories_from_turn(
        store,
        user_input="记住明天改简历",
        source_message_id=None,
        budget=budget,
    ) == []


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    return TestClient(app)


def test_chat_complete_triggers_auto_memory_write(client: TestClient) -> None:
    response = client.post(
        "/chat/complete",
        json={"messages": [{"role": "user", "content": "记住我今晚要改简历"}]},
    )
    assert response.status_code == 200

    memories = client.get("/memory/memories", params={"type": "reminder"}).json()["memories"]
    assert len(memories) == 1
    assert "今晚要改简历" in memories[0]["content"]
