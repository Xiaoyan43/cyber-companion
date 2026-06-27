"""Shared Soul Layer runtime (Phase 1).

`SoulTurnRuntime.run_turn()` is the single turn orchestrator that replaces the
soul-turn编排 duplicated across the text / Pipecat / RTC entry points. See
docs/SOUL_RUNTIME_ARCH.md §3 for the contract.
"""

from backend.app.soul.adapters import (
    NoopAgendaPort,
    NoopEventLogPort,
    SQLiteAgendaPort,
    SQLiteEventLogPort,
    SQLiteMemoryPort,
    SQLiteStatePort,
    SoulPorts,
    ports_from_store,
)
from backend.app.soul.ports import (
    AgendaPort,
    EventLogPort,
    MemoryPort,
    OpenLoopDraft,
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
    "AgendaPort",
    "OpenLoopDraft",
    "SQLiteMemoryPort",
    "SQLiteStatePort",
    "SQLiteEventLogPort",
    "SQLiteAgendaPort",
    "NoopEventLogPort",
    "NoopAgendaPort",
    "ports_from_store",
    "tag_reply_by_sentence",
]
