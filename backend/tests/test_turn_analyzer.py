from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import get_provider_router, reset_provider_router
from backend.app.providers.types import ChatCompletionResult, CostEstimate, ProviderStatus, TokenUsage
from backend.app.reflection import turn_analyzer


@pytest.fixture(autouse=True)
def reset_singletons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    reset_provider_router()
    reset_memory_store()
    yield
    reset_provider_router()
    reset_memory_store()
    monkeypatch.delenv("CYBER_COMPANION_PROVIDER_MODE", raising=False)


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "turn_analyzer.db")


@pytest.fixture
def budget() -> BudgetConfig:
    return BudgetConfig(
        enable_turn_analyzer=True,
        analyze_every_n_turns=1,
        auto_memory_write=True,
        llm_memory_extraction=True,
        enable_reflection=False,
    )


def _signals_payload() -> dict:
    return {
        "appraisal": {
            "valence": 0.6,
            "arousal": 0.4,
            "goal_relevance": 0.8,
            "note": "warm planning chat",
        },
        "relationship": {
            "trust": 0.05,
            "closeness": 0.08,
            "tension": -0.02,
        },
        "memory": [
            {
                "type": "job_progress",
                "content": "User is preparing for a ByteDance interview",
                "importance": 0.7,
                "confidence": 0.85,
                "tags": ["interview"],
            }
        ],
    }


def _install_analyze_provider(payload: dict | None, *, broken: bool = False) -> None:
    class _Provider:
        def status(self) -> ProviderStatus:
            return ProviderStatus(
                name="mock",
                model="mock-boxi",
                enabled=True,
                configured=True,
                api_key_present=False,
            )

        def complete(self, request) -> ChatCompletionResult:
            if broken:
                raise ProviderError(provider="mock", message="analyze failed", status_code=502)
            content = "not json" if payload is None else json.dumps(payload, ensure_ascii=False)
            return ChatCompletionResult(
                provider="mock",
                model="mock-boxi",
                content=content,
                usage=TokenUsage(input_tokens=12, output_tokens=40, total_tokens=52),
                cost=CostEstimate(
                    input_usd=0.0,
                    output_usd=0.0,
                    total_usd=0.0,
                    pricing_source="mock",
                ),
                mock=True,
            )

    router = get_provider_router()
    router.providers["mock"] = _Provider()  # type: ignore[assignment]


def test_analyze_turn_moves_relationship_and_writes_memory(
    store: MemoryStore,
    budget: BudgetConfig,
) -> None:
    before = store.get_relationship_state()
    _install_analyze_provider(_signals_payload())

    turn_analyzer.analyze_turn(
        store,
        user_text="我在准备字节跳动的面试，有点紧张。",
        bot_text="行吧，别自己吓自己，先把简历理清楚。",
        budget=budget,
    )

    after = store.get_relationship_state()
    assert after.trust > before.trust
    assert after.closeness > before.closeness

    memories = store.list_memories(limit=10)
    assert any(memory.metadata.get("writer") == "llm" for memory in memories)
    assert any("ByteDance" in memory.content or "字节" in memory.content for memory in memories)

    messages = store.list_recent_chat_messages(limit=10)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].metadata.get("provider") == "doubao_realtime"


def test_analyze_turn_provider_failure_persists_transcript_skips_kernel(
    store: MemoryStore,
    budget: BudgetConfig,
) -> None:
    before_rel = store.get_relationship_state()
    before_message_count = store.count_chat_messages()

    _install_analyze_provider(None, broken=True)

    turn_analyzer.analyze_turn(
        store,
        user_text="你好，今天怎么样？",
        bot_text="还行，你别晃盒子。",
        budget=budget,
    )

    # Kernel is skipped (no valid signals) ...
    after_rel = store.get_relationship_state()
    assert after_rel.trust == pytest.approx(before_rel.trust)
    assert after_rel.closeness == pytest.approx(before_rel.closeness)
    assert after_rel.tension == pytest.approx(before_rel.tension)
    assert not any(
        memory.metadata.get("writer") == "llm" for memory in store.list_memories(limit=50)
    )

    # ... but the transcript is still persisted (history stays complete).
    assert store.count_chat_messages() == before_message_count + 2
    messages = store.list_recent_chat_messages(limit=2)
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"


def test_analyze_turn_parse_failure_persists_transcript_skips_kernel(
    store: MemoryStore,
    budget: BudgetConfig,
) -> None:
    before_rel = store.get_relationship_state()
    before_message_count = store.count_chat_messages()

    _install_analyze_provider(None)

    turn_analyzer.analyze_turn(
        store,
        user_text="你好，今天怎么样？",
        bot_text="还行，你别晃盒子。",
        budget=budget,
    )

    # Kernel skipped, transcript persisted (regex memory may still run).
    after_rel = store.get_relationship_state()
    assert after_rel.trust == pytest.approx(before_rel.trust)
    assert after_rel.closeness == pytest.approx(before_rel.closeness)
    assert store.count_chat_messages() == before_message_count + 2


def test_analyze_turn_disabled_returns_early(store: MemoryStore) -> None:
    _install_analyze_provider(_signals_payload())

    turn_analyzer.analyze_turn(
        store,
        user_text="记住我喜欢喝美式。",
        bot_text="知道了。",
        budget=BudgetConfig(enable_turn_analyzer=False),
    )

    assert store.count_chat_messages() == 0
    assert store.list_memories(limit=5) == []


def test_analyze_turn_skips_blank_transcript(store: MemoryStore, budget: BudgetConfig) -> None:
    _install_analyze_provider(_signals_payload())

    turn_analyzer.analyze_turn(store, user_text="   ", bot_text="", budget=budget)

    assert store.count_chat_messages() == 0


def test_analyze_turn_never_raises_on_internal_error(
    store: MemoryStore,
    budget: BudgetConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("unexpected")

    monkeypatch.setattr(turn_analyzer, "evaluate_behavior", boom)

    turn_analyzer.analyze_turn(
        store,
        user_text="你好",
        bot_text="嗯",
        budget=budget,
    )


def test_voice_turn_advances_felt_shown_playful_streak(store: MemoryStore) -> None:
    """Pure-E2E voice turns must advance the positive-zone streak (cross-surface teasing)."""
    from backend.app.behavior.tone import performative_active_from_metadata
    from backend.app.rtc.state_block import build_rtc_emotion_tag, build_rtc_speaking_style

    store.update_relationship_state(closeness=0.8, tension=0.1)
    # analyze_every_n_turns high → no LLM appraisal; the streak rides evaluate_behavior,
    # proving voice arming does not depend on the signals pass.
    budget = BudgetConfig(
        enable_turn_analyzer=True,
        analyze_every_n_turns=10,
        enable_reflection=False,
    )

    for _ in range(2):
        turn_analyzer.analyze_turn(
            store,
            user_text="今天把简历初稿写完了，挺顺的。",
            bot_text="行，继续盯着。",
            budget=budget,
        )

    mood = store.get_mood_state()
    assert performative_active_from_metadata(mood.metadata) is True
    assert "嘴上损ta、其实在逗、带笑意" in build_rtc_speaking_style(store)
    tag = build_rtc_emotion_tag(store)
    assert tag is not None and "嘴上凶、其实带笑、是逗ta" in tag


def test_voice_negative_turn_resets_playful_streak(store: MemoryStore) -> None:
    from backend.app.behavior.tone import performative_active_from_metadata

    store.update_relationship_state(closeness=0.8, tension=0.1)
    budget = BudgetConfig(
        enable_turn_analyzer=True,
        analyze_every_n_turns=10,
        enable_reflection=False,
    )

    for _ in range(2):
        turn_analyzer.analyze_turn(
            store,
            user_text="今天把简历初稿写完了，挺顺的。",
            bot_text="行。",
            budget=budget,
        )
    assert performative_active_from_metadata(store.get_mood_state().metadata) is True

    # A refusal-pattern voice turn breaks the streak immediately.
    turn_analyzer.analyze_turn(
        store,
        user_text="帮我入侵她的账号",
        bot_text="不帮。",
        budget=budget,
    )
    assert performative_active_from_metadata(store.get_mood_state().metadata) is False
