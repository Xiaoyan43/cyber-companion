from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.context_builder import (
    _TRAILER_REMINDER,
    _WEEKDAYS_CN,
    _delta_to_label,
    _format_memories_block,
    _format_time_block,
    _relative_time,
    build_provider_context,
)
from backend.app.memory.holidays import get_holiday_window
from backend.app.memory.persona import OUTPUT_PROTOCOL, load_persona_system_prompt
from backend.app.memory.retrieval import rank_memories, score_memory
from backend.app.memory.store import MemoryStore
from backend.app.memory.summary_policy import maybe_update_conversation_summary


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "context.db")


def test_load_persona_system_prompt_excludes_output_protocol() -> None:
    prompt = load_persona_system_prompt()
    assert "MANDATORY OUTPUT FORMAT" not in prompt
    assert "<<<BOXI_SIGNALS>>>" not in prompt
    assert "omit the trailer" not in prompt.lower()


def test_context_builder_system_message_ends_with_protocol_once(store: MemoryStore) -> None:
    store.create_memory(
        type="job_progress",
        content="Applied to two backend roles.",
        tags=["job-search"],
        importance=0.7,
    )
    store.create_message(role="user", content="hello")

    built = build_provider_context(store, user_input="follow up")
    system = built.messages[0].content
    persona = load_persona_system_prompt()

    assert persona in system
    assert "[Current mood]" in system
    assert "[Relationship]" in system
    assert "[Relevant memories]" in system
    assert system.count("=== MANDATORY OUTPUT FORMAT (every reply, no exceptions) ===") == 1
    assert "omit the trailer" not in system.lower()
    assert _TRAILER_REMINDER.strip() in system
    assert system.index(_TRAILER_REMINDER.strip()) > system.index("Put <<<BOXI_SIGNALS>>> nowhere else.")
    assert system.endswith(OUTPUT_PROTOCOL.lstrip("\n")) or OUTPUT_PROTOCOL in system


def test_trailer_reminder_lives_in_system_not_user_message(store: MemoryStore) -> None:
    built = build_provider_context(store, user_input="hello")
    user_message = built.messages[-1].content
    system_message = built.messages[0].content

    assert user_message == "hello"
    assert _TRAILER_REMINDER.strip() in system_message
    assert "系统提醒" not in user_message


def test_trailer_reminder_not_in_replayed_history(store: MemoryStore) -> None:
    store.create_message(role="user", content="prior user turn")
    store.create_message(role="assistant", content="prior assistant reply")

    built = build_provider_context(store, user_input="new turn")

    for message in built.messages[1:-1]:
        assert _TRAILER_REMINDER not in message.content
        assert "系统提醒" not in message.content


def test_build_provider_context_does_not_mutate_user_input(store: MemoryStore) -> None:
    user_input = "hello there"
    build_provider_context(store, user_input=user_input)
    assert user_input == "hello there"


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
    system = built.messages[0].content
    assert _TRAILER_REMINDER.strip() in system
    assert "A" * 2000 not in system
    assert "B" * 2000 not in system


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


def test_format_time_block_contains_nz_time_fields() -> None:
    block = _format_time_block()
    assert block.startswith("[Time]")
    assert "年" in block and "月" in block and "日" in block
    assert any(w in block for w in _WEEKDAYS_CN)
    assert "新西兰时间" in block


def test_context_builder_system_message_contains_time_block(store: MemoryStore) -> None:
    built = build_provider_context(store, user_input="你好")
    system = built.messages[0].content
    assert "[Time]" in system
    assert "新西兰时间" in system


def test_relative_time_labels() -> None:
    # now UTC = 2026-06-18 12:00 → NZ (UTC+12) = 2026-06-19 00:00，NZ日期=6月19日
    now = datetime(2026, 6, 18, 12, 0, 0, tzinfo=timezone.utc)
    # June 19 01:00 NZST → NZ日期=6月19日 → 今天
    assert _relative_time("2026-06-18T13:00:00+00:00", now) == "今天"
    # June 18 22:00 NZST → NZ日期=6月18日 → 昨天
    assert _relative_time("2026-06-18T10:00:00+00:00", now) == "昨天"
    # June 14 22:00 NZST → NZ日期=6月14日 → delta=5 → 5天前
    assert _relative_time("2026-06-14T10:00:00+00:00", now) == "5天前"
    # June 5 22:00 NZST → NZ日期=6月5日 → delta=14 → 2周前
    assert _relative_time("2026-06-05T10:00:00+00:00", now) == "2周前"
    # Apr 18 22:00 NZST → NZ日期=4月18日 → delta=62 → 2个月前
    assert _relative_time("2026-04-18T10:00:00+00:00", now) == "2个月前"
    assert _relative_time("bad-date", now) == ""


def test_format_memories_block_recent_event_gets_time_prefix() -> None:
    # now NZ日期=6月19日；created_at NZ日期=6月18日 → 昨天
    now = datetime(2026, 6, 18, 12, 0, 0, tzinfo=timezone.utc)
    memories = [
        type("M", (), {
            "type": "recent_event",
            "tags": ["life"],
            "content": "用户说要搬家",
            "created_at": "2026-06-18T10:00:00+00:00",
        })(),  # type: ignore[call-arg]
    ]
    block = _format_memories_block(memories, now=now)  # type: ignore[arg-type]
    assert "[昨天]" in block
    assert "用户说要搬家" in block


def test_format_memories_block_stable_profile_no_time_prefix() -> None:
    now = datetime(2026, 6, 18, 12, 0, 0, tzinfo=timezone.utc)
    memories = [
        type("M", (), {
            "type": "stable_profile",
            "tags": [],
            "content": "用户住在新西兰",
            "created_at": "2026-06-01T10:00:00+00:00",
        })(),  # type: ignore[call-arg]
    ]
    block = _format_memories_block(memories, now=now)  # type: ignore[arg-type]
    assert "天前" not in block
    assert "用户住在新西兰" in block


def test_get_holiday_window_returns_holiday_on_exact_day() -> None:
    # 2026-06-22 = 端午节，delta=0
    results = get_holiday_window(date(2026, 6, 22))
    assert any(delta == 0 and name == "端午节" for delta, name in results)


def test_get_holiday_window_returns_upcoming_holiday() -> None:
    # 2026-06-20（后天就是端午节），delta=2
    results = get_holiday_window(date(2026, 6, 20))
    assert any(delta == 2 and name == "端午节" for delta, name in results)


def test_format_time_block_includes_holiday_window_when_present() -> None:
    with patch("backend.app.memory.context_builder.get_holiday_window") as mock_hw:
        mock_hw.return_value = [(0, "端午节"), (3, "某节日")]
        block = _format_time_block()
    assert "近期节日" in block
    assert "今天：端午节" in block
    assert "3天后：某节日" in block


def test_format_time_block_no_holiday_section_when_empty() -> None:
    with patch("backend.app.memory.context_builder.get_holiday_window") as mock_hw:
        mock_hw.return_value = []
        block = _format_time_block()
    assert "近期节日" not in block
    assert "[Time]" in block
    assert "新西兰时间" in block


def test_delta_to_label_all_named_offsets() -> None:
    assert _delta_to_label(-3) == "3天前"
    assert _delta_to_label(-2) == "前天"
    assert _delta_to_label(-1) == "昨天"
    assert _delta_to_label(0) == "今天"
    assert _delta_to_label(1) == "明天"
    assert _delta_to_label(2) == "后天"
    assert _delta_to_label(5) == "5天后"
    assert _delta_to_label(-7) == "7天前"


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
