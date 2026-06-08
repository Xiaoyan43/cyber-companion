from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.providers.router import reset_provider_router


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
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


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "memory.db")


def test_init_database_creates_all_tables(store: MemoryStore) -> None:
    import sqlite3

    connection = sqlite3.connect(store.db_path)
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    connection.close()

    assert {
        "messages",
        "conversation_summaries",
        "memories",
        "mood_state",
        "reminders",
        "file_access_log",
        "schema_meta",
    }.issubset(tables)


def test_message_create_and_list(store: MemoryStore) -> None:
    store.create_message(role="user", content="你好")
    store.create_message(role="assistant", content="嗯")

    messages = store.list_messages()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"


def test_memory_crud(store: MemoryStore) -> None:
    created = store.create_memory(
        type="stable_profile",
        content="User prefers concise replies.",
        tags=["preference"],
        importance=0.8,
        confidence=0.9,
    )

    fetched = store.get_memory(created.id)
    assert fetched is not None
    assert fetched.content == "User prefers concise replies."

    updated = store.update_memory(created.id, content="User prefers blunt concise replies.")
    assert updated is not None
    assert updated.content == "User prefers blunt concise replies."

    assert store.delete_memory(created.id) is True
    assert store.get_memory(created.id) is None


def test_mood_state_defaults_and_update(store: MemoryStore) -> None:
    mood = store.get_mood_state()
    assert mood.mood == "idle"

    updated = store.update_mood_state(mood="annoyed", annoyance=0.7)
    assert updated.mood == "annoyed"
    assert updated.annoyance == 0.7


def test_chat_complete_empty_submit_skips_blank_user_row(client: TestClient) -> None:
    response = client.post(
        "/chat/complete",
        json={"messages": [{"role": "user", "content": "   "}]},
    )

    assert response.status_code == 200

    messages = client.get("/memory/messages").json()["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["metadata"]["decision"] == "silent"


def test_chat_complete_persists_messages(client: TestClient) -> None:
    response = client.post(
        "/chat/complete",
        json={"messages": [{"role": "user", "content": "记住我今晚要改简历"}]},
    )

    assert response.status_code == 200

    messages = client.get("/memory/messages").json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "记住我今晚要改简历"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["metadata"]["provider"] == "mock"


def test_memory_api_create_and_list(client: TestClient) -> None:
    create_response = client.post(
        "/memory/memories",
        json={
            "type": "job_progress",
            "content": "Applied to two backend roles this week.",
            "tags": ["job-search"],
            "importance": 0.7,
            "confidence": 0.8,
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["type"] == "job_progress"

    list_response = client.get("/memory/memories", params={"type": "job_progress"})
    assert list_response.status_code == 200
    assert len(list_response.json()["memories"]) == 1


def test_memory_api_rejects_unknown_type(client: TestClient) -> None:
    response = client.post(
        "/memory/memories",
        json={"type": "unknown_type", "content": "nope"},
    )

    assert response.status_code == 400
    assert "Unsupported memory type" in response.json()["detail"]["error"]


def _age_memory(store: MemoryStore, memory_id: int, updated_at: str) -> None:
    from backend.app.memory.database import connect

    with connect(store.db_path) as connection:
        connection.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?",
            (updated_at, memory_id),
        )


def test_behavior_evaluate_persists_idle_tick_mutter(client: TestClient) -> None:
    from backend.app.memory.store import get_memory_store

    store = get_memory_store()
    store.update_mood_state(boredom=0.52, loneliness=0.52)

    response = client.post("/behavior/evaluate", json={"event_type": "idle_tick"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["decision"] == "mutter"
    assert payload["saved_message_id"] is not None

    messages = client.get("/memory/messages").json()["messages"]
    assert len(messages) == 1
    assert messages[0]["id"] == payload["saved_message_id"]
    assert messages[0]["role"] == "assistant"
    assert messages[0]["source"] == "behavior_tick"
    assert messages[0]["metadata"]["decision"] == "mutter"
    assert messages[0]["metadata"]["behavior_event"] == "idle_tick"


def test_behavior_evaluate_persists_proactive_check(client: TestClient) -> None:
    from backend.app.memory.store import get_memory_store

    store = get_memory_store()
    memory = store.create_memory(
        type="job_progress",
        content="Applied to two backend roles.",
        tags=["job-search"],
    )
    _age_memory(store, memory.id, "2020-01-01T00:00:00+00:00")

    response = client.post("/behavior/evaluate", json={"event_type": "proactive_check"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["decision"] == "proactive"
    assert payload["saved_message_id"] is not None

    messages = client.get("/memory/messages").json()["messages"]
    assert len(messages) == 1
    assert messages[0]["metadata"]["behavior_event"] == "proactive_check"


def test_behavior_evaluate_observe_does_not_persist(client: TestClient) -> None:
    response = client.post("/behavior/evaluate", json={"event_type": "idle_tick"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["decision"] == "observe"
    assert payload["saved_message_id"] is None

    messages = client.get("/memory/messages").json()["messages"]
    assert messages == []
