from pathlib import Path

import pytest

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.context_builder import build_provider_context
from backend.app.memory.retrieval import rank_memories, score_memory
from backend.app.memory.store import MemoryStore
from backend.app.memory.summary_policy import maybe_update_conversation_summary


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "context.db")


def test_rank_memories_prefers_job_progress_for_resume_query(store: MemoryStore) -> None:
    store.create_memory(type="stable_profile", content="User likes concise replies.", importance=0.8)
    job_memory = store.create_memory(
        type="job_progress",
        content="Applied to two backend roles this week.",
        tags=["job-search"],
        importance=0.7,
        confidence=0.9,
    )
    store.create_memory(type="recent_event", content="Ate instant noodles.", importance=0.3)

    ranked = rank_memories(store.list_memories(), "我今晚还要改简历吗")
    assert ranked[0].id == job_memory.id


def test_context_builder_uses_default_budget_when_omitted(store: MemoryStore) -> None:
    store.create_message(role="user", content="hello")

    built = build_provider_context(store, user_input="follow up")

    assert built.messages[-1].content == "follow up"
    assert built.estimated_input_tokens <= BudgetConfig().max_input_tokens_per_turn
    assert len(built.included_message_ids) <= BudgetConfig().max_raw_turns


def test_context_builder_limits_raw_turns_and_uses_summary(store: MemoryStore) -> None:
    budget = BudgetConfig(
        max_input_tokens_per_turn=4000,
        max_output_tokens_per_turn=300,
        max_raw_turns=2,
        max_memories_per_turn=3,
        summary_batch_size=4,
    )

    for index in range(8):
        role = "user" if index % 2 == 0 else "assistant"
        store.create_message(role=role, content=f"turn-{index}")

    store.create_conversation_summary(
        range_start_message_id=1,
        range_end_message_id=4,
        summary="Older turns were mostly complaining about the box.",
        keywords=["box", "complain"],
    )

    built = build_provider_context(
        store,
        user_input="turn-8",
        budget=budget,
    )

    assert built.total_stored_messages == 8
    assert built.summary_used is not None
    assert len(built.included_message_ids) <= budget.max_raw_turns
    assert built.estimated_input_tokens <= budget.max_input_tokens_per_turn
    assert built.messages[-1].content == "turn-8"
    assert "Older turns were mostly complaining" in built.messages[0].content


def test_context_builder_does_not_include_full_transcript(store: MemoryStore) -> None:
    budget = BudgetConfig(max_raw_turns=2, max_memories_per_turn=2, summary_batch_size=4)

    for index in range(20):
        role = "user" if index % 2 == 0 else "assistant"
        store.create_message(role=role, content=f"message-{index}")

    built = build_provider_context(
        store,
        user_input="message-20",
        budget=budget,
    )

    non_system_contents = [
        message.content for message in built.messages if message.role != "system"
    ]

    assert "message-0" not in non_system_contents
    assert "message-2" not in non_system_contents
    assert len(built.included_message_ids) <= budget.max_raw_turns
    assert len(built.messages) <= budget.max_raw_turns + 2


def test_context_builder_respects_small_token_budget(store: MemoryStore) -> None:
    store.create_memory(type="stable_profile", content="A" * 2000, importance=0.9)
    store.create_memory(type="project", content="B" * 2000, importance=0.8)

    built = build_provider_context(
        store,
        user_input="short question",
        budget=BudgetConfig(max_input_tokens_per_turn=300, max_memories_per_turn=5),
    )

    assert built.truncated is True
    assert built.estimated_input_tokens <= 300


def test_summary_policy_creates_summary_for_old_batch(store: MemoryStore) -> None:
    budget = BudgetConfig(max_raw_turns=2, summary_batch_size=4, llm_summary=False)

    for index in range(10):
        role = "user" if index % 2 == 0 else "assistant"
        store.create_message(role=role, content=f"chunk-{index}")

    created = maybe_update_conversation_summary(store, budget=budget)
    assert created is True
    latest = store.get_latest_conversation_summary()
    assert latest is not None
    assert "chunk-0" in latest.summary


def test_score_memory_is_deterministic(store: MemoryStore) -> None:
    memory = store.create_memory(
        type="job_progress",
        content="Sent resume to two companies.",
        tags=["job-search"],
        importance=0.7,
        confidence=0.8,
    )

    first = score_memory(memory, "job search progress")
    second = score_memory(memory, "job search progress")
    assert first == second


def test_sql_recent_chat_excludes_behavior_tick_and_counts_chat_only(store: MemoryStore) -> None:
    budget = BudgetConfig(
        max_raw_turns=2,
        max_memories_per_turn=2,
        summary_batch_size=4,
        llm_summary=False,
    )

    for index in range(6):
        role = "user" if index % 2 == 0 else "assistant"
        store.create_message(role=role, content=f"chat-{index}")

    for index in range(20):
        store.create_message(
            role="assistant",
            content=f"idle-{index}",
            source="behavior_tick",
        )

    built = build_provider_context(store, user_input="chat-6", budget=budget)

    assert built.total_stored_messages == 6
    assert len(built.included_message_ids) == budget.max_raw_turns
    non_system_contents = [
        message.content for message in built.messages if message.role != "system"
    ]
    assert "chat-4" in non_system_contents
    assert "chat-5" in non_system_contents
    assert "chat-2" not in non_system_contents
    assert not any(content.startswith("idle-") for content in non_system_contents)

    for index in range(4):
        role = "user" if index % 2 == 0 else "assistant"
        store.create_message(role=role, content=f"extra-{index}")

    assert maybe_update_conversation_summary(store, budget=budget) is True
    latest = store.get_latest_conversation_summary()
    assert latest is not None
    assert "chat-0" in latest.summary


def test_context_builder_excludes_behavior_tick_lines(store: MemoryStore) -> None:
    budget = BudgetConfig(max_raw_turns=4, max_memories_per_turn=2)
    store.create_message(role="user", content="real question one")
    store.create_message(role="assistant", content="real answer one")
    store.create_message(
        role="assistant",
        content="嗯。你到底要不要说正事。",
        source="behavior_tick",
    )

    built = build_provider_context(store, user_input="real question two", budget=budget)

    non_system_contents = [
        message.content for message in built.messages if message.role != "system"
    ]
    assert "嗯。你到底要不要说正事。" not in non_system_contents
    assert "real answer one" in non_system_contents


def test_summary_policy_ignores_behavior_tick_lines(store: MemoryStore) -> None:
    budget = BudgetConfig(max_raw_turns=2, summary_batch_size=4)
    for index in range(10):
        store.create_message(
            role="assistant",
            content=f"idle-mutter-{index}",
            source="behavior_tick",
        )

    # Only behavior-tick lines exist, so there is no real conversation to recap.
    assert maybe_update_conversation_summary(store, budget=budget) is False
    assert store.get_latest_conversation_summary() is None
