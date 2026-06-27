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
    OpenLoopRecord,
    RelationshipStateRecord,
)
from backend.app.memory.usage_guard import BudgetGate
from backend.app.providers.types import ChatCompletionResult


@dataclass(frozen=True)
class SoulEvent:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None


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


@dataclass(frozen=True)
class OpenLoopDraft:
    """Write payload for ``AgendaPort.upsert`` (§4 ``upsert(loop)``).

    ``loop_id`` is the dedup key: set it to update an existing loop, leave it
    ``None`` to create. Mirrors ``MemoryStore.upsert_open_loop`` kwargs.
    """

    kind: str
    title: str
    summary: str = ""
    status: str = "open"
    due_at: str | None = None
    last_mentioned_at: str | None = None
    source_message_id: int | None = None
    priority: float = 0.5
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    loop_id: int | None = None


class AgendaPort(Protocol):
    """Open loops / future events / agenda (§4). Phase 3B reads only; the
    runtime does not write through it yet.
    """

    def open_loops(
        self,
        *,
        status: str | None = "open",
        due_before: str | None = None,
        limit: int = 50,
    ) -> list[OpenLoopRecord]: ...

    def upsert(self, draft: OpenLoopDraft) -> OpenLoopRecord | None: ...

    def close(self, loop_id: int) -> OpenLoopRecord | None: ...
