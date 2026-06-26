from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.app.behavior.types import BehaviorDecision
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.context_builder import BuiltContext
from backend.app.memory.database import (
    ConversationSummaryRecord,
    MemoryRecord,
    MoodStateRecord,
    RelationshipStateRecord,
)
from backend.app.memory.usage_guard import BudgetGate
from backend.app.providers.types import ChatCompletionResult


@dataclass(frozen=True)
class SoulEvent:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


class StatePort(Protocol):
    def get_mood(self) -> MoodStateRecord: ...

    def get_relationship(self) -> RelationshipStateRecord: ...

    def apply_signals(self, signals: dict | None) -> None: ...


class MemoryPort(Protocol):
    def decide_user_message(self, user_input: str) -> BehaviorDecision: ...

    def check_llm_budget(
        self,
        budget: BudgetConfig,
        *,
        target_model: str,
    ) -> BudgetGate: ...

    def build_context(
        self,
        *,
        user_input: str,
        budget: BudgetConfig,
        behavior: BehaviorDecision,
        target_language: str | None = None,
    ) -> BuiltContext: ...

    def persist_turn(
        self,
        *,
        user_input: str,
        result: ChatCompletionResult,
        decision: str,
        avatar_state: str,
        should_call_llm: bool,
        translation: str | None = None,
    ) -> list[int]: ...

    def record_turn_memories(
        self,
        *,
        user_input: str,
        signals: dict | None,
        source_message_id: int | None,
        budget: BudgetConfig,
    ) -> list[MemoryRecord]: ...

    def maybe_update_summary(self, budget: BudgetConfig) -> bool: ...

    def note_llm_turn(self) -> int: ...

    def latest_summary(self) -> ConversationSummaryRecord | None: ...


class EventLogPort(Protocol):
    def append(self, event: SoulEvent) -> None: ...

    def tail(
        self,
        *,
        kinds: set[str] | None = None,
        limit: int = 50,
    ) -> list[SoulEvent]: ...

