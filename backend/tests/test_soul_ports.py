from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.behavior.types import BehaviorDecision
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.context_builder import BuiltContext
from backend.app.memory.database import (
    ConversationSummaryRecord,
    MemoryRecord,
    MoodStateRecord,
    RelationshipStateRecord,
)
from backend.app.memory.store import MemoryStore
from backend.app.memory.usage_guard import BudgetGate
from backend.app.providers.cost import estimate_cost, estimate_usage
from backend.app.providers.router import get_provider_router, reset_provider_router
from backend.app.providers.types import ChatCompletionResult
from backend.app.soul.adapters import SoulPorts, ports_from_store
from backend.app.soul.ports import SoulEvent
from backend.app.soul.runtime import PerceivedEvent, SoulTurnRuntime


class _FakeStatePort:
    def __init__(self) -> None:
        self.applied_signals: list[dict | None] = []

    def get_mood(self) -> MoodStateRecord:
        return MoodStateRecord(
            updated_at="2000-01-01T00:00:00+00:00",
            mood="idle",
            energy=0.7,
            annoyance=0.1,
            boredom=0.1,
            worry=0.1,
            trust=0.5,
            loneliness=0.2,
        )

    def get_relationship(self) -> RelationshipStateRecord:
        return RelationshipStateRecord(
            updated_at="2000-01-01T00:00:00+00:00",
            trust=0.5,
            closeness=0.2,
            familiarity=0.0,
            tension=0.0,
            last_meaningful_interaction_at=None,
            metadata={},
        )

    def apply_signals(self, signals: dict | None) -> None:
        self.applied_signals.append(signals)


class _FakeMemoryPort:
    def __init__(self) -> None:
        self.persisted_turns: list[dict[str, object]] = []
        self.recorded_turns: list[dict[str, object]] = []
        self.updated_summary = False
        self.llm_turns = 0

    def decide_user_message(self, user_input: str) -> BehaviorDecision:
        return BehaviorDecision(
            decision="mutter",
            avatar_state="annoyed",
            should_call_llm=False,
            reason="fake_local_path",
            local_response="哼，听见了。",
        )

    def check_llm_budget(
        self,
        budget: BudgetConfig,
        *,
        target_model: str,
    ) -> BudgetGate:
        raise AssertionError("local fake turn should not check the budget")

    def build_context(
        self,
        *,
        user_input: str,
        budget: BudgetConfig,
        behavior: BehaviorDecision,
        target_language: str | None = None,
    ) -> BuiltContext:
        raise AssertionError("local fake turn should not build provider context")

    def persist_turn(
        self,
        *,
        user_input: str,
        result: ChatCompletionResult,
        decision: str,
        avatar_state: str,
        should_call_llm: bool,
        translation: str | None = None,
    ) -> list[int]:
        self.persisted_turns.append(
            {
                "user_input": user_input,
                "content": result.content,
                "decision": decision,
                "avatar_state": avatar_state,
                "should_call_llm": should_call_llm,
                "translation": translation,
            }
        )
        return [1, 2]

    def record_turn_memories(
        self,
        *,
        user_input: str,
        signals: dict | None,
        source_message_id: int | None,
        budget: BudgetConfig,
    ) -> list[MemoryRecord]:
        self.recorded_turns.append(
            {
                "user_input": user_input,
                "signals": signals,
                "source_message_id": source_message_id,
            }
        )
        return []

    def maybe_update_summary(self, budget: BudgetConfig) -> bool:
        self.updated_summary = True
        return False

    def note_llm_turn(self) -> int:
        self.llm_turns += 1
        return self.llm_turns

    def latest_summary(self) -> ConversationSummaryRecord | None:
        return None


class _FakeEventLogPort:
    def __init__(self) -> None:
        self.events: list[SoulEvent] = []

    def append(self, event: SoulEvent) -> None:
        self.events.append(event)

    def tail(
        self,
        *,
        kinds: set[str] | None = None,
        limit: int = 50,
    ) -> list[SoulEvent]:
        events = self.events
        if kinds is not None:
            events = [event for event in events if event.kind in kinds]
        return events[-limit:]


@pytest.fixture(autouse=True)
def _router_env(monkeypatch: pytest.MonkeyPatch):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("CYBER_COMPANION_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("CYBER_COMPANION_PROVIDER_MODE", "mock")
    reset_provider_router()
    yield
    reset_provider_router()


def test_runtime_accepts_fake_ports_without_memorystore() -> None:
    memory = _FakeMemoryPort()
    state = _FakeStatePort()
    event_log = _FakeEventLogPort()
    runtime = SoulTurnRuntime(
        ports=SoulPorts(
            memory=memory,
            state=state,
            event_log=event_log,
        ),
        router=get_provider_router(),
        budget=BudgetConfig(),
    )

    outcome = runtime.run_turn(
        PerceivedEvent(event_type="user_message", user_input="嗯", surface="text")
    )

    assert outcome.result.content == "哼，听见了。"
    assert outcome.called_llm is False
    assert outcome.decision == "mutter"
    assert memory.persisted_turns == [
        {
            "user_input": "嗯",
            "content": "哼，听见了。",
            "decision": "mutter",
            "avatar_state": "annoyed",
            "should_call_llm": False,
            "translation": None,
        }
    ]
    assert memory.recorded_turns == [
        {"user_input": "嗯", "signals": None, "source_message_id": 1}
    ]
    assert memory.updated_summary is True
    assert memory.llm_turns == 0
    assert state.applied_signals == []
    assert len(event_log.events) == 1
    event = event_log.events[0]
    assert event.kind == "turn.committed"
    assert event.payload["surface"] == "text"
    assert event.payload["decision"] == "mutter"
    assert event.payload["called_llm"] is False
    assert event.payload["message_ids"] == [1, 2]
    assert event.payload["has_user_input"] is True


def test_sqlite_ports_wrap_memorystore_and_event_log(tmp_path: Path) -> None:
    store = MemoryStore(db_path=tmp_path / "ports.db")
    ports = ports_from_store(store)
    usage = estimate_usage(["记住 我叫小明"], "记下了。")
    result = ChatCompletionResult(
        provider="local-test",
        model="local-test",
        content="记下了。",
        usage=usage,
        cost=estimate_cost("mock-boxi", usage),
        mock=True,
    )

    saved_ids = ports.memory.persist_turn(
        user_input="记住 我叫小明",
        result=result,
        decision="reply",
        avatar_state="talking",
        should_call_llm=False,
    )
    ports.memory.record_turn_memories(
        user_input="记住 我叫小明",
        signals=None,
        source_message_id=saved_ids[0],
        budget=BudgetConfig(),
    )
    ports.memory.maybe_update_summary(BudgetConfig())
    ports.memory.note_llm_turn()
    ports.event_log.append(SoulEvent(kind="turn.persisted", payload={"surface": "test"}))

    assert saved_ids == [1, 2]
    assert store.count_chat_messages() == 2
    assert store.get_meta("turns_since_reflection", "0") == "1"
    assert sorted(memory.content for memory in store.list_memories()) == [
        "User profile: 小明",
        "我叫小明",
    ]
    events = ports.event_log.tail()
    assert len(events) == 1
    assert events[0].id == 1
    assert events[0].created_at
    assert events[0].kind == "turn.persisted"
    assert events[0].payload == {"surface": "test"}
