from __future__ import annotations

from dataclasses import dataclass

from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.kernel import apply_signals_to_kernel
from backend.app.behavior.types import BehaviorDecision, BehaviorEvent
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.chat_persistence import persist_chat_turn
from backend.app.memory.context_builder import BuiltContext, build_provider_context
from backend.app.memory.database import (
    ConversationSummaryRecord,
    MemoryRecord,
    MoodStateRecord,
    RelationshipStateRecord,
)
from backend.app.memory.store import MemoryStore
from backend.app.memory.summary_policy import maybe_update_conversation_summary
from backend.app.memory.usage_guard import BudgetGate, evaluate_llm_budget_gate
from backend.app.memory.write_policy import record_turn_memories
from backend.app.providers.types import ChatCompletionResult
from backend.app.schemas import ChatMessageSchema
from backend.app.soul.ports import EventLogPort, MemoryPort, SoulEvent, StatePort


@dataclass(frozen=True)
class SoulPorts:
    memory: MemoryPort
    state: StatePort
    event_log: EventLogPort


class SQLiteStatePort:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def get_mood(self) -> MoodStateRecord:
        return self._store.get_mood_state()

    def get_relationship(self) -> RelationshipStateRecord:
        return self._store.get_relationship_state()

    def apply_signals(self, signals: dict | None) -> None:
        apply_signals_to_kernel(self._store, signals)


class SQLiteMemoryPort:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def decide_user_message(self, user_input: str) -> BehaviorDecision:
        return evaluate_behavior(
            self._store,
            BehaviorEvent(event_type="user_message", user_input=user_input),
        )

    def check_llm_budget(
        self,
        budget: BudgetConfig,
        *,
        target_model: str,
    ) -> BudgetGate:
        return evaluate_llm_budget_gate(
            self._store,
            budget,
            target_model=target_model,
        )

    def build_context(
        self,
        *,
        user_input: str,
        budget: BudgetConfig,
        behavior: BehaviorDecision,
        target_language: str | None = None,
    ) -> BuiltContext:
        return build_provider_context(
            self._store,
            user_input=user_input,
            budget=budget,
            behavior=behavior,
            target_language=target_language,
        )

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
        return persist_chat_turn(
            self._store,
            [ChatMessageSchema(role="user", content=user_input)],
            result,
            decision=decision,
            avatar_state=avatar_state,
            should_call_llm=should_call_llm,
            translation=translation,
        )

    def record_turn_memories(
        self,
        *,
        user_input: str,
        signals: dict | None,
        source_message_id: int | None,
        budget: BudgetConfig,
    ) -> list[MemoryRecord]:
        return record_turn_memories(
            self._store,
            user_input=user_input,
            signals=signals,
            source_message_id=source_message_id,
            budget=budget,
        )

    def maybe_update_summary(self, budget: BudgetConfig) -> bool:
        return maybe_update_conversation_summary(self._store, budget=budget)

    def note_llm_turn(self) -> int:
        return self._store.note_llm_turn()

    def latest_summary(self) -> ConversationSummaryRecord | None:
        return self._store.get_latest_conversation_summary()


class NoopEventLogPort:
    def append(self, event: SoulEvent) -> None:
        return None

    def tail(
        self,
        *,
        kinds: set[str] | None = None,
        limit: int = 50,
    ) -> list[SoulEvent]:
        return []


def ports_from_store(store: MemoryStore) -> SoulPorts:
    return SoulPorts(
        memory=SQLiteMemoryPort(store),
        state=SQLiteStatePort(store),
        event_log=NoopEventLogPort(),
    )

