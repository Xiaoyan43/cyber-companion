from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.memory.write_policy import (
    extract_memory_candidates,
    maybe_write_memories_from_turn,
    record_turn_memories,
    write_memories_from_signals,
)
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


def _profile_memories(store: MemoryStore):
    return store.list_memories(type="stable_profile", limit=20)


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
    assert written[0].content == "投递: 两份后端简历"
    assert "我今天" not in written[0].content


def test_low_value_input_writes_nothing(store: MemoryStore) -> None:
    assert maybe_write_memories_from_turn(store, user_input="嗯", source_message_id=None) == []


def test_similar_memory_updates_instead_of_duplicating(store: MemoryStore) -> None:
    store.create_memory(
        type="job_progress",
        content="投递: 两份后端简历",
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
    assert written[0].content == "投递: 两份后端简历"
    assert written[0].confidence >= 0.65


@pytest.mark.parametrize(
    "user_input",
    [
        "我是说你别拖了",
        "我是不是该改简历",
        "i am tired",
    ],
)
def test_profile_loose_triggers_do_not_write(store: MemoryStore, user_input: str) -> None:
    maybe_write_memories_from_turn(store, user_input=user_input, source_message_id=None)
    assert _profile_memories(store) == []


def test_profile_explicit_name_still_writes(store: MemoryStore) -> None:
    written = maybe_write_memories_from_turn(
        store,
        user_input="我叫张伟",
        source_message_id=None,
    )

    assert len(written) == 1
    assert written[0].type == "stable_profile"
    assert "张伟" in written[0].content


def test_preference_requires_imperative_anchor(store: MemoryStore) -> None:
    assert extract_memory_candidates("我觉得你说话太冲了") == []

    written = maybe_write_memories_from_turn(
        store,
        user_input="请说话简短一点",
        source_message_id=None,
    )
    assert len(written) == 1
    assert written[0].type == "behavior_preference"
    assert "简短" in written[0].content


def test_project_below_confidence_threshold_is_skipped(store: MemoryStore) -> None:
    assert extract_memory_candidates("我在做一个赛博伴侣项目") == []
    assert maybe_write_memories_from_turn(
        store,
        user_input="我在做一个赛博伴侣项目",
        source_message_id=None,
    ) == []


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


def test_write_memories_from_signals_persists_llm_writer(store: MemoryStore) -> None:
    user_message = store.create_message(role="user", content="随便聊聊")

    written = write_memories_from_signals(
        store,
        [
            {
                "type": "job_progress",
                "content": "Rejected by Company X on 2026-06-09",
                "importance": 0.7,
                "confidence": 0.9,
                "tags": ["job-search"],
            }
        ],
        source_message_id=user_message.id,
    )

    assert len(written) == 1
    assert written[0].type == "job_progress"
    assert written[0].metadata["writer"] == "llm"
    assert "Company X" in written[0].content


def test_validate_signal_memory_rejects_unknown_type(store: MemoryStore) -> None:
    assert (
        write_memories_from_signals(
            store,
            [{"type": "garbage", "content": "should not persist", "confidence": 0.9}],
            source_message_id=None,
        )
        == []
    )


def test_validate_signal_memory_rejects_low_confidence(store: MemoryStore) -> None:
    assert (
        write_memories_from_signals(
            store,
            [{"type": "job_progress", "content": "Low confidence fact", "confidence": 0.4}],
            source_message_id=None,
        )
        == []
    )


def test_validate_signal_memory_clamps_importance_and_confidence(store: MemoryStore) -> None:
    written = write_memories_from_signals(
        store,
        [
            {
                "type": "recent_event",
                "content": "Clamped importance and confidence",
                "importance": 5,
                "confidence": 2,
            }
        ],
        source_message_id=None,
    )

    assert len(written) == 1
    assert written[0].importance == 1.0
    assert written[0].confidence == 1.0


def test_signal_memory_dedup_updates_in_place(store: MemoryStore) -> None:
    store.create_memory(
        type="job_progress",
        content="Rejected by Company X on 2026-06-09",
        tags=["job-search"],
        importance=0.6,
        confidence=0.7,
    )

    written = write_memories_from_signals(
        store,
        [
            {
                "type": "job_progress",
                "content": "Rejected by Company X on 2026-06-09",
                "importance": 0.8,
                "confidence": 0.9,
            }
        ],
        source_message_id=None,
    )

    assert len(written) == 1
    assert len(store.list_memories(type="job_progress", limit=10)) == 1
    assert written[0].metadata["writer"] == "llm"


def test_write_memories_from_signals_caps_at_five(store: MemoryStore) -> None:
    items = [
        {
            "type": "recent_event",
            "content": f"Signal memory item number {index}",
            "confidence": 0.9,
        }
        for index in range(8)
    ]

    written = write_memories_from_signals(store, items, source_message_id=None)

    assert len(written) == 5


def test_record_turn_memories_picks_m3_over_regex(store: MemoryStore) -> None:
    user_message = store.create_message(role="user", content="嗯")

    written = record_turn_memories(
        store,
        user_input="嗯",
        signals={
            "memory": [
                {
                    "type": "stable_profile",
                    "content": "User prefers concise bullet replies",
                    "confidence": 0.85,
                }
            ]
        },
        source_message_id=user_message.id,
        budget=BudgetConfig(llm_memory_extraction=True),
    )

    assert len(written) == 1
    assert written[0].type == "stable_profile"
    assert written[0].metadata["writer"] == "llm"
    assert "concise bullet" in written[0].content


def test_record_turn_memories_falls_back_to_regex_m2(store: MemoryStore) -> None:
    written = record_turn_memories(
        store,
        user_input="记住明天改简历",
        signals=None,
        source_message_id=None,
        budget=BudgetConfig(llm_memory_extraction=True),
    )

    assert len(written) == 1
    assert written[0].type == "reminder"
    assert written[0].metadata["writer"] == "rule_based"


def test_record_turn_memories_falls_back_when_all_llm_items_invalid(store: MemoryStore) -> None:
    written = record_turn_memories(
        store,
        user_input="记住明天改简历",
        signals={
            "memory": [
                {"type": "bogus", "content": "Invalid type should be rejected", "confidence": 0.9}
            ]
        },
        source_message_id=None,
        budget=BudgetConfig(llm_memory_extraction=True),
    )

    assert len(written) == 1
    assert written[0].type == "reminder"
    assert written[0].metadata["writer"] == "rule_based"


def test_record_turn_memories_valid_m3_does_not_also_run_regex(store: MemoryStore) -> None:
    written = record_turn_memories(
        store,
        user_input="我叫张伟",
        signals={
            "memory": [
                {
                    "type": "stable_profile",
                    "content": "User prefers concise bullet replies",
                    "confidence": 0.85,
                }
            ]
        },
        source_message_id=None,
        budget=BudgetConfig(llm_memory_extraction=True),
    )

    assert len(written) == 1
    assert written[0].metadata["writer"] == "llm"
    assert "concise bullet" in written[0].content
    # The regex M2 path (which would have written a "User profile: 张伟" stable_profile)
    # must not run when M3 already wrote something.
    assert len(store.list_memories(type="stable_profile", limit=10)) == 1


def test_record_turn_memories_invalid_m3_and_no_regex_writes_nothing(store: MemoryStore) -> None:
    written = record_turn_memories(
        store,
        user_input="嗯",
        signals={
            "memory": [
                {"type": "bogus", "content": "Invalid type should be rejected", "confidence": 0.9}
            ]
        },
        source_message_id=None,
        budget=BudgetConfig(llm_memory_extraction=True),
    )

    assert written == []
    assert store.list_memories(limit=10) == []


def test_record_turn_memories_respects_llm_knob_off(store: MemoryStore) -> None:
    written = record_turn_memories(
        store,
        user_input="嗯",
        signals={
            "memory": [
                {
                    "type": "stable_profile",
                    "content": "Only from signals, not regex",
                    "confidence": 0.9,
                }
            ]
        },
        source_message_id=None,
        budget=BudgetConfig(llm_memory_extraction=False),
    )

    assert written == []


def test_record_turn_memories_respects_auto_memory_write_gate(store: MemoryStore) -> None:
    budget = BudgetConfig(auto_memory_write=False)

    assert (
        record_turn_memories(
            store,
            user_input="记住明天改简历",
            signals={"memory": [{"type": "reminder", "content": "From signals", "confidence": 0.9}]},
            source_message_id=None,
            budget=budget,
        )
        == []
    )
    assert (
        record_turn_memories(
            store,
            user_input="记住明天改简历",
            signals=None,
            source_message_id=None,
            budget=budget,
        )
        == []
    )
