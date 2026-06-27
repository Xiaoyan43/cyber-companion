"""Turn-consistency contract (docs/SOUL_RUNTIME_ARCH.md §5 缺口).

Same perceived input + same model reply MUST produce the same kernel/memory
side-effects across surfaces, even though the spoken/streamed text differs:

  - text surface  → ``SoulTurnRuntime.run_turn`` (tags the reply via the tagger)
  - voice surface → ``CompanionBrain.stream_turn`` (plain text) + ``remember`` →
                    ``SoulTurnRuntime.commit_turn``

We deliberately do NOT compare the persisted assistant *content* (text is tagged,
voice is plain — a legitimate surface difference) nor volatile timestamps. The
contract is over the durable soul state: mood/relationship kernel, written
memories, persisted message count, and LLM-turn accounting.

A fixed provider returns one identical raw reply (+signals trailer) and usage for
every call, so the only differences exercised are the orchestration paths
themselves — not prompt shape (voice appends a voice-mode system message) and not
the tagger's own provider calls.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from backend.app.behavior.parser import SIGNALS_SENTINEL
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore
from backend.app.providers.cost import estimate_cost
from backend.app.providers.mock import MockProvider
from backend.app.providers.router import get_provider_router, reset_provider_router
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, TokenUsage
from backend.app.soul import PerceivedEvent, SoulTurnRuntime
from backend.realtime.companion_brain import CompanionBrain

# Visible reply + a signals trailer that drives BOTH a memory write (signal path)
# and a kernel update (appraisal/relationship). Kept mild on purpose: valence and
# goal_relevance stay < 0.5 so apply_signals_to_kernel does not stamp a fresh
# ``last_meaningful_interaction_at`` (which would be the one non-deterministic field).
_REPLY_VISIBLE = "嗯，我都记下了。"
_REPLY_SIGNALS = {
    "avatar_state": "talking",
    "decision": "reply",
    "appraisal": {"valence": 0.3, "goal_relevance": 0.3},
    "relationship": {"trust": 0.05, "closeness": 0.05},
    "memory": [
        {
            "type": "stable_profile",
            "content": "用户在做赛博伴侣项目",
            "importance": 0.8,
            "confidence": 0.9,
        }
    ],
}
_REPLY_RAW = f"{_REPLY_VISIBLE}\n{SIGNALS_SENTINEL}\n{json.dumps(_REPLY_SIGNALS, ensure_ascii=False)}"
_FIXED_USAGE = TokenUsage(input_tokens=64, output_tokens=12, total_tokens=76)

_ALL_TIME = "2000-01-01 00:00:00"


class _FixedReplyProvider(MockProvider):
    """Deterministic provider — identical raw reply + usage for every call."""

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        return ChatCompletionResult(
            provider=self.name,
            model="mock-boxi",
            content=_REPLY_RAW,
            usage=_FIXED_USAGE,
            cost=estimate_cost("mock-boxi", _FIXED_USAGE),
            mock=True,
        )

    def complete_stream(self, request: ChatCompletionRequest):
        yield ("delta", _REPLY_RAW)
        yield ("usage", _FIXED_USAGE)


@pytest.fixture
def router(monkeypatch: pytest.MonkeyPatch):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    reset_provider_router()
    provider_router = get_provider_router()
    provider_router.providers["mock"] = _FixedReplyProvider()
    yield provider_router
    reset_provider_router()


def _kernel_snapshot(store: MemoryStore) -> dict[str, object]:
    mood = store.get_mood_state()
    rel = store.get_relationship_state()
    return {
        "mood": mood.mood,
        "energy": round(mood.energy, 6),
        "annoyance": round(mood.annoyance, 6),
        "boredom": round(mood.boredom, 6),
        "worry": round(mood.worry, 6),
        "loneliness": round(mood.loneliness, 6),
        "trust": round(rel.trust, 6),
        "closeness": round(rel.closeness, 6),
        "familiarity": round(rel.familiarity, 6),
        "tension": round(rel.tension, 6),
    }


def _memory_snapshot(store: MemoryStore) -> list[tuple]:
    return sorted(
        (
            memory.type,
            memory.content,
            round(memory.importance, 6),
            round(memory.confidence, 6),
            tuple(sorted(memory.tags)),
            memory.source_message_id,
        )
        for memory in store.list_memories(limit=200)
    )


def _run_text(router, budget: BudgetConfig, db_path: Path, user_input: str) -> MemoryStore:
    store = MemoryStore(db_path=db_path)
    SoulTurnRuntime(store=store, router=router, budget=budget).run_turn(
        PerceivedEvent(event_type="user_message", user_input=user_input, surface="text")
    )
    return store


async def _drive_voice(brain: CompanionBrain, user_input: str):
    outcome = None
    async for kind, value in brain.stream_turn(user_input):
        if kind == "done":
            outcome = value
    assert outcome is not None
    return outcome


def _run_voice(router, budget: BudgetConfig, db_path: Path, user_input: str) -> tuple[MemoryStore, object]:
    store = MemoryStore(db_path=db_path)
    brain = CompanionBrain(store, router=router, budget=budget)
    outcome = asyncio.run(_drive_voice(brain, user_input))
    brain.remember(outcome)
    return store, outcome


def _assert_side_effects_match(text_store: MemoryStore, voice_store: MemoryStore) -> None:
    assert _kernel_snapshot(text_store) == _kernel_snapshot(voice_store)
    assert _memory_snapshot(text_store) == _memory_snapshot(voice_store)
    assert text_store.count_chat_messages() == voice_store.count_chat_messages()
    assert text_store.count_llm_turns_since(_ALL_TIME) == voice_store.count_llm_turns_since(_ALL_TIME)


def test_llm_turn_side_effects_match_across_surfaces(router, tmp_path: Path) -> None:
    budget = BudgetConfig()
    user_input = "我想跟你认真聊聊我最近在忙的事"

    text_store = _run_text(router, budget, tmp_path / "text_llm.db", user_input)
    voice_store, outcome = _run_voice(router, budget, tmp_path / "voice_llm.db", user_input)

    # Both must actually take the LLM path for this contract to mean anything.
    assert outcome.called_llm is True
    _assert_side_effects_match(text_store, voice_store)

    # Non-vacuous: the signal-driven memory write and the LLM-turn note really happened.
    assert len(_memory_snapshot(text_store)) == 1
    assert text_store.count_llm_turns_since(_ALL_TIME) == 1
    assert text_store.count_chat_messages() == 2


def test_local_turn_side_effects_match_across_surfaces(router, tmp_path: Path) -> None:
    budget = BudgetConfig()
    user_input = "嗯"  # low-value → local behavior line, no LLM call

    text_store = _run_text(router, budget, tmp_path / "text_local.db", user_input)
    voice_store, outcome = _run_voice(router, budget, tmp_path / "voice_local.db", user_input)

    # Both must stay on the local (no-LLM) path.
    assert outcome.called_llm is False
    _assert_side_effects_match(text_store, voice_store)

    # Local path writes no memory and notes no LLM turn on either surface.
    assert _memory_snapshot(text_store) == []
    assert text_store.count_llm_turns_since(_ALL_TIME) == 0
