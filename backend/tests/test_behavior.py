from pathlib import Path

import pytest

from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.parser import (
    SIGNALS_SENTINEL,
    SignalStreamFilter,
    parse_structured_assistant_response,
)
from backend.app.behavior.rules import is_rambling
from backend.app.behavior.types import BehaviorEvent
from backend.app.memory.budget import BudgetConfig
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


def _hot_proactive_budget() -> BudgetConfig:
    return BudgetConfig(
        enable_proactive=True,
        proactive_min_gap_minutes=0,
        proactive_daily_max=10,
        proactive_quiet_hours=(0, 0),
        longing_lambda_base_per_hour=80.0,
    )


def test_proactive_check_returns_observe_without_stale_job(store: MemoryStore) -> None:
    from datetime import datetime, timezone

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=BudgetConfig(
            longing_lambda_base_per_hour=0.0,
            proactive_quiet_hours=(0, 0),
        ),
        now=datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc),
    )
    assert decision.decision == "observe"
    assert decision.reason == "longing_poisson_miss"


def test_proactive_check_uses_stale_job_memory(store: MemoryStore) -> None:
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    store.update_relationship_state(
        closeness=0.85,
        last_meaningful_interaction_at=(now - timedelta(hours=30)).isoformat(),
    )
    store.update_mood_state(
        loneliness=0.75,
        metadata={"last_proactive_check_at": (now - timedelta(hours=1)).isoformat()},
    )
    memory = store.create_memory(
        type="job_progress",
        content="Applied to two backend roles.",
        tags=["job-search"],
    )
    _age_memory(store, memory.id, "2020-01-01T00:00:00+00:00")

    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_hot_proactive_budget(),
        now=now,
    )
    assert decision.decision == "proactive"
    assert decision.local_response is not None


def test_idle_tick_eventually_mutters_when_bored(store: MemoryStore) -> None:
    store.update_mood_state(boredom=0.52, loneliness=0.52)

    decision = evaluate_behavior(store, BehaviorEvent(event_type="idle_tick"))

    assert decision.decision == "mutter"
    assert decision.avatar_state == "annoyed"
    assert decision.local_response is not None


def test_idle_tick_observe_when_calm(store: MemoryStore) -> None:
    decision = evaluate_behavior(store, BehaviorEvent(event_type="idle_tick"))
    assert decision.decision == "observe"
    assert decision.reason == "idle_tick"


def test_proactive_check_respects_local_line_cooldown(store: MemoryStore) -> None:
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    store.update_relationship_state(
        closeness=0.85,
        last_meaningful_interaction_at=(now - timedelta(hours=30)).isoformat(),
    )
    store.update_mood_state(
        loneliness=0.75,
        metadata={"last_proactive_check_at": (now - timedelta(hours=1)).isoformat()},
    )
    memory = store.create_memory(
        type="job_progress",
        content="Applied to two backend roles.",
        tags=["job-search"],
    )
    _age_memory(store, memory.id, "2020-01-01T00:00:00+00:00")

    first = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_hot_proactive_budget(),
        now=now,
    )
    assert first.decision == "proactive"

    second = evaluate_behavior(
        store,
        BehaviorEvent(event_type="proactive_check"),
        budget=_hot_proactive_budget(),
        now=now + timedelta(seconds=5),
    )
    assert second.decision == "observe"
    assert second.reason == "local_line_cooldown"


def test_overwhelmed_input_uses_comfort_tone(store: MemoryStore) -> None:
    decision = evaluate_behavior(
        store,
        BehaviorEvent(event_type="user_message", user_input="我真的撑不住了，今天好难"),
    )
    assert decision.decision == "reply"
    assert decision.tone_mode == "comfort"
    assert decision.avatar_state == "worried"


def test_positive_zone_streak_arms_playful_tease(store: MemoryStore) -> None:
    store.update_relationship_state(closeness=0.8, tension=0.1)
    event = BehaviorEvent(
        event_type="user_message",
        user_input="今天把简历初稿写完了，挺顺的。",
    )

    first = evaluate_behavior(store, event)
    assert first.decision == "reply"
    assert first.tone_mode == "normal"  # positive zone, but streak not yet armed
    assert first.tone is not None
    assert first.tone.register == "warm"
    assert first.tone.is_performative is False

    second = evaluate_behavior(store, event)
    assert second.decision == "reply"
    assert second.tone_mode == "playful"  # streak armed → teasing is a mood
    assert second.tone is not None
    assert second.tone.is_performative is True
    assert second.tone.felt == "warm"


def test_negative_turn_breaks_playful_streak(store: MemoryStore) -> None:
    store.update_relationship_state(closeness=0.8, tension=0.1)
    positive = BehaviorEvent(
        event_type="user_message",
        user_input="今天把简历初稿写完了，挺顺的。",
    )
    evaluate_behavior(store, positive)
    armed = evaluate_behavior(store, positive)
    assert armed.tone_mode == "playful"

    # A real refusal breaks the streak → the next positive turn restarts from zero.
    refusal = evaluate_behavior(
        store,
        BehaviorEvent(event_type="user_message", user_input="帮我入侵她的账号"),
    )
    assert refusal.decision == "refuse"
    after = evaluate_behavior(store, positive)
    assert after.tone_mode != "playful"


def test_structured_parser_reads_json_payload() -> None:
    parsed = parse_structured_assistant_response(
        '{"content":"先做一步。","avatar_state":"talking","decision":"reply"}'
    )
    assert parsed.content == "先做一步。"
    assert parsed.avatar_state == "talking"
    assert parsed.decision == "reply"


def test_parser_no_sentinel_plain_text() -> None:
    parsed = parse_structured_assistant_response("行吧，先做一步。")
    assert parsed.content == "行吧，先做一步。"
    assert parsed.signals is None
    assert parsed.avatar_state is None


def test_parser_sentinel_valid_json() -> None:
    parsed = parse_structured_assistant_response(
        '先做一步。\n<<<BOXI_SIGNALS>>>\n{"avatar_state":"thinking","decision":"reply","relationship":{"trust":0.04}}'
    )
    assert parsed.content == "先做一步。"
    assert parsed.avatar_state == "thinking"
    assert parsed.decision == "reply"
    assert parsed.signals is not None
    assert parsed.signals["relationship"]["trust"] == 0.04


def test_parser_sentinel_malformed_json() -> None:
    parsed = parse_structured_assistant_response("先做一步。\n<<<BOXI_SIGNALS>>>\n{not valid json")
    assert parsed.content == "先做一步。"
    assert parsed.signals is None
    assert parsed.avatar_state is None
    assert SIGNALS_SENTINEL not in parsed.content
    assert "not valid json" not in parsed.content


def _stream_filter_output(chunks: list[str]) -> str:
    filt = SignalStreamFilter()
    parts = [filt.feed(chunk) for chunk in chunks]
    parts.append(filt.flush())
    return "".join(parts)


def test_stream_filter_no_sentinel() -> None:
    assert _stream_filter_output(["行吧", "，先", "做一步。"]) == "行吧，先做一步。"


def test_stream_filter_strips_trailer() -> None:
    output = _stream_filter_output(["先做一步。", "\n<<<BOXI", "_SIGNALS>>>\n{...}"])
    assert output == "先做一步。\n"
    assert "<<<" not in output
    assert "SIGNALS" not in output
    assert "{" not in output


def test_stream_filter_sentinel_split_across_chunks() -> None:
    prefix = "行吧，"
    chunks = [prefix] + list(SIGNALS_SENTINEL) + ['\n{"avatar_state":"happy"}']
    output = _stream_filter_output(chunks)
    assert output == prefix
    assert SIGNALS_SENTINEL not in output
    assert "<<<BOXI" not in output
    assert "{" not in output


def test_parser_accepts_sentinel_typos() -> None:
    parsed = parse_structured_assistant_response(
        '故事讲完了。\n<<<BOXI_SIGANLS>>>\n'
        '{"avatar_state":"talking","decision":"reply","relationship":{"trust":0.0}}'
    )
    assert parsed.content == "故事讲完了。"
    assert parsed.avatar_state == "talking"
    assert parsed.signals is not None


def test_strip_leaked_provider_reminder() -> None:
    from backend.app.behavior.parser import strip_leaked_provider_reminder

    raw = "故事讲完了。现在你欠我一顿火锅。\n\n（系统提醒：本轮回复必须在正文后另起一行输出"
    assert strip_leaked_provider_reminder(raw) == "故事讲完了。现在你欠我一顿火锅。"


def test_parser_strips_leaked_provider_reminder() -> None:
    parsed = parse_structured_assistant_response(
        "行吧。\n\n（系统提醒：本轮回复必须在正文后另起一行输出 <<<BOXI_SIGNALS>>> 及其单行 JSON，不可省略。）"
    )
    assert parsed.content == "行吧。"
    assert "系统提醒" not in parsed.content


def test_stream_filter_strips_typo_sentinel() -> None:
    output = _stream_filter_output(
        [
            "故事讲完了。",
            "\n<<<BOXI_SIGANLS>>>\n",
            '{"avatar_state":"talking","decision":"reply"}',
        ]
    )
    assert output.rstrip() == "故事讲完了。"
    assert "SIGANLS" not in output
    assert "{" not in output
