"""Companion Brain — custom LLM slot inside the Pipecat pipeline (V2 Phase 1+).

Mirrors the soul seam used by ``/chat/complete`` in ``backend.app.main``:
behavior → context → provider → memory write. Phase 0 proves imports only.
"""

from __future__ import annotations

from typing import Any

from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.types import BehaviorDecision, BehaviorEvent
from backend.app.memory.context_builder import build_provider_context
from backend.app.memory.persona import load_persona_system_prompt
from backend.app.memory.store import MemoryStore
from backend.app.memory.write_policy import record_turn_memories
from backend.app.providers.router import get_provider_router

# Soul seam imports — referenced here so Phase 0 proves they resolve without Pipecat.
_SOUL_IMPORTS = (
    evaluate_behavior,
    build_provider_context,
    get_provider_router,
    record_turn_memories,
    load_persona_system_prompt,
)


class CompanionBrain:
    """Future Pipecat LLM-step wrapper around the existing Python soul.

    Phase 1 will wire ``decide`` → ``respond`` → ``remember`` into the voice
    pipeline; stubs raise until then.
    """

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def decide(self, user_text: str) -> BehaviorDecision:
        """Run the behavior engine for an incoming user utterance.

        Phase 1: call ``evaluate_behavior`` like ``chat_complete`` does with
        ``BehaviorEvent(event_type="user_message", user_input=user_text)``.
        """
        raise NotImplementedError("V2 Phase 1")

    def respond(
        self, user_text: str
    ) -> tuple[str, str, dict[str, Any] | None]:
        """Produce reply text, avatar state, and optional signals trailer.

        Phase 1: ``build_provider_context`` + ``get_provider_router().complete``
        + ``parse_structured_assistant_response`` (see ``main.chat_complete``).
        Returns ``(reply_text, avatar_state, signals)``.
        """
        raise NotImplementedError("V2 Phase 1")

    def remember(
        self,
        user_text: str,
        signals: dict[str, Any] | None,
        *,
        source_message_id: int | None = None,
    ) -> None:
        """Persist turn memories from signals (M3) with regex M2 fallback.

        Phase 1: call ``record_turn_memories`` after the assistant reply is saved.
        """
        raise NotImplementedError("V2 Phase 1")
