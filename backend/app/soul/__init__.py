"""Shared Soul Layer runtime (Phase 1).

`SoulTurnRuntime.run_turn()` is the single turn orchestrator that replaces the
soul-turn编排 duplicated across the text / Pipecat / RTC entry points. See
docs/SOUL_RUNTIME_ARCH.md §3 for the contract.
"""

from backend.app.soul.runtime import (
    PerceivedEvent,
    SoulTurnRuntime,
    TurnOutcome,
    tag_reply_by_sentence,
)

__all__ = [
    "PerceivedEvent",
    "SoulTurnRuntime",
    "TurnOutcome",
    "tag_reply_by_sentence",
]
