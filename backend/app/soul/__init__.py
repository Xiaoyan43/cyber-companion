"""Shared Soul Layer runtime (Phase 1).

`SoulTurnRuntime.run_turn()` is the single turn orchestrator that replaces the
soul-turn编排 duplicated across the text / Pipecat / RTC entry points. See
docs/SOUL_RUNTIME_ARCH.md §3 for the contract.
"""

from backend.app.soul.adapters import (
    NoopEventLogPort,
    SQLiteEventLogPort,
    SQLiteMemoryPort,
    SQLiteStatePort,
    SoulPorts,
    ports_from_store,
)
from backend.app.soul.ports import (
    EventLogPort,
    MemoryPort,
    SoulEvent,
    StatePort,
)
from backend.app.soul.runtime import (
    PerceivedEvent,
    SoulTurnRuntime,
    TurnOutcome,
    tag_reply_by_sentence,
)

__all__ = [
    "PerceivedEvent",
    "SoulTurnRuntime",
    "SoulEvent",
    "SoulPorts",
    "TurnOutcome",
    "MemoryPort",
    "StatePort",
    "EventLogPort",
    "SQLiteMemoryPort",
    "SQLiteStatePort",
    "SQLiteEventLogPort",
    "NoopEventLogPort",
    "ports_from_store",
    "tag_reply_by_sentence",
]
