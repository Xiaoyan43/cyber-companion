"""Shadow ``MemoryPort`` spike: canonical SQLite + best-effort candidate mirror.

Not registered in ``ports_from_store``. Candidate failures are swallowed and
recorded via diagnostics only (no memory content).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.app.behavior.types import BehaviorDecision
from backend.app.memory.adapters.contract import (
    CandidateMemoryBackend,
    memory_record_to_candidate_dto,
)
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.context_builder import BuiltContext
from backend.app.memory.database import ConversationSummaryRecord, MemoryRecord
from backend.app.memory.usage_guard import BudgetGate
from backend.app.providers.types import ChatCompletionResult
from backend.app.soul.ports import MemoryPort

DiagnosticSink = Callable[[str, dict[str, Any]], None]


class ShadowMemoryPort:
    """Delegates all canonical behavior to SQLite; mirrors ``MemoryRecord`` writes."""

    def __init__(
        self,
        canonical: MemoryPort,
        candidate: CandidateMemoryBackend,
        *,
        diagnostics: DiagnosticSink | None = None,
    ) -> None:
        self._canonical = canonical
        self._candidate = candidate
        self._diagnostics = diagnostics or (lambda _event, _payload: None)

    def decide_user_message(self, user_input: str) -> BehaviorDecision:
        return self._canonical.decide_user_message(user_input)

    def check_llm_budget(
        self,
        budget: BudgetConfig,
        *,
        target_model: str,
    ) -> BudgetGate:
        return self._canonical.check_llm_budget(budget, target_model=target_model)

    def build_context(
        self,
        *,
        user_input: str,
        budget: BudgetConfig,
        behavior: BehaviorDecision,
        target_language: str | None = None,
    ) -> BuiltContext:
        return self._canonical.build_context(
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
        return self._canonical.persist_turn(
            user_input=user_input,
            result=result,
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
        records = self._canonical.record_turn_memories(
            user_input=user_input,
            signals=signals,
            source_message_id=source_message_id,
            budget=budget,
        )
        self._mirror_records(records)
        return records

    def maybe_update_summary(self, budget: BudgetConfig) -> bool:
        return self._canonical.maybe_update_summary(budget)

    def note_llm_turn(self) -> int:
        return self._canonical.note_llm_turn()

    def latest_summary(self) -> ConversationSummaryRecord | None:
        return self._canonical.latest_summary()

    def _mirror_records(self, records: list[MemoryRecord]) -> None:
        if not records:
            return
        mirrored = 0
        failures = 0
        for record in records:
            try:
                self._candidate.write(memory_record_to_candidate_dto(record))
                mirrored += 1
            except Exception as exc:
                failures += 1
                self._diagnostics(
                    "candidate_mirror_failed",
                    {
                        "backend": self._candidate.backend_name,
                        "namespace": self._candidate.namespace,
                        "error_type": type(exc).__name__,
                        "memory_type": record.type,
                        "record_id": record.id,
                    },
                )
        if mirrored:
            self._diagnostics(
                "candidate_mirror_succeeded",
                {
                    "backend": self._candidate.backend_name,
                    "namespace": self._candidate.namespace,
                    "count": mirrored,
                },
            )
        if failures:
            self._diagnostics(
                "candidate_mirror_batch_partial",
                {
                    "backend": self._candidate.backend_name,
                    "namespace": self._candidate.namespace,
                    "failures": failures,
                    "attempted": len(records),
                },
            )
