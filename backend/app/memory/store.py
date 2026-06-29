"""MemoryStore — SQLite-backed source of truth for the Shared Soul.

The implementation is split into topical mixins (one file per concern) to keep
each file small and maintainable; ``MemoryStore`` assembles them into a single
class with an unchanged public API. Import paths are stable: continue to use
``from backend.app.memory.store import MemoryStore, get_memory_store``.

- ``_store_messages``  : chat messages + LLM cost/turn accounting
- ``_store_memories``  : memories CRUD + memory links
- ``_store_loops``     : soul-event log + open loops (agenda)
- ``_store_state``     : mood / relationship / existential / behavior-runtime (kernel)
- ``_store_records``   : conversation summaries, reminders, file-access log
- ``_store_meta``      : schema_meta + reflection / turn-analysis locks
- ``_store_helpers``   : shared pure helpers (no DB access)
"""

from __future__ import annotations

from pathlib import Path

from backend.app.memory._store_loops import OpenLoopsAndEventsMixin
from backend.app.memory._store_memories import MemoriesMixin
from backend.app.memory._store_messages import MessagesMixin
from backend.app.memory._store_meta import MetaMixin
from backend.app.memory._store_records import RecordsMixin
from backend.app.memory._store_state import StateMixin
from backend.app.memory.database import init_database, resolve_db_path


class MemoryStore(
    MessagesMixin,
    MemoriesMixin,
    OpenLoopsAndEventsMixin,
    StateMixin,
    RecordsMixin,
    MetaMixin,
):
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = resolve_db_path(db_path)
        init_database(self.db_path)


_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


def reset_memory_store() -> None:
    global _store
    _store = None
