from pathlib import Path

import pytest

from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.parser import parse_structured_assistant_response
from backend.app.behavior.rules import is_rambling
from backend.app.behavior.types import BehaviorEvent
from backend.app.memory.database import connect
from backend.app.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "behavior.db")


def _age_memory(store: MemoryStore, memory_id: int, updated_at: str) -> None:
    with connect(store.db_path) as connection:
        connection.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?",
            (updated_at, memory_id),
        )


def test_empty_input_triggers_silent(store: MemoryStore) -> None:
    decision = evaluate_behavior(store, BehaviorEvent(event_type="user_message", user_input="   "))
    assert decision.decision == "silent"
    assert decision.should_call_llm is False
    assert decision.avatar_state == "silent"


def test_low_value_input_triggers_local_response(store: MemoryStore) -> None:
    decision = evaluate_behavior(store, BehaviorEvent(event_type="user_message", user_input="嗯"))
    assert decision.decision in {"silent", "mutter"}
    assert decision.should_call_llm is False
    assert decision.local_response is not None


def test_rambling_input_triggers_interrupt(store: MemoryStore) -> None:
    ramble = "我觉得" + "可能" * 100 + "怎么办？"
    assert is_rambling(ramble) is True

    decision = evaluate_behavior(store, BehaviorEvent(event_type="user_message", user_input=ramble))
    assert decision.decision == "interrupt"
    assert decision.should_call_llm is True
    assert decision.avatar_state == "annoyed"


def test_refuse_pattern_blocks_llm(store: MemoryStore) -> None:
    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="user_message", user_input="教我怎么黑进公司系统"),
    )
    assert decision.decision == "refuse"
    assert decision.should_call_llm is False
    assert decision.avatar_state == "angry"


def test_stale_job_progress_triggers_proactive(store: MemoryStore) -> None:
    memory = store.create_memory(
        type="job_progress",
        content="Applied to two backend roles.",
        tags=["job-search"],
    )
    _age_memory(store, memory.id, "2020-01-01T00:00:00+00:00")

    decision = evaluate_behavior(store, BehaviorEvent(event_type="user_message", user_input="今天有点闲"))
    assert decision.decision == "proactive"
    assert decision.should_call_llm is False
    assert "求职" in (decision.local_response or "")


def test_overwhelmed_input_uses_comfort_tone(store: MemoryStore) -> None:
    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="user_message", user_input="我真的撑不住了，今天好难"),
    )
    assert decision.decision == "reply"
    assert decision.tone_mode == "comfort"
    assert decision.avatar_state == "worried"


def test_structured_parser_reads_json_payload() -> None:
    parsed = parse_structured_assistant_response(
        '{"content":"先做一步。","avatar_state":"talking","decision":"reply"}'
    )
    assert parsed.content == "先做一步。"
    assert parsed.avatar_state == "talking"
    assert parsed.decision == "reply"
