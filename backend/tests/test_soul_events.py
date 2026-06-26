from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "soul_events.db")


def test_soul_event_append_and_tail(store: MemoryStore) -> None:
    first = store.append_soul_event(kind="turn.committed", payload={"surface": "text"})
    second = store.append_soul_event(kind="agenda.created", payload={"loop_id": 7})
    third = store.append_soul_event(kind="turn.committed", payload={"surface": "pipecat"})

    assert first.id == 1
    assert second.id == 2
    assert third.id == 3

    events = store.tail_soul_events(limit=2)
    assert [event.id for event in events] == [2, 3]
    assert [event.kind for event in events] == ["agenda.created", "turn.committed"]

    turn_events = store.tail_soul_events(kinds={"turn.committed"}, limit=10)
    assert [event.id for event in turn_events] == [1, 3]
    assert turn_events[0].payload == {"surface": "text"}
    assert turn_events[1].payload == {"surface": "pipecat"}


def test_soul_event_tail_handles_empty_filters(store: MemoryStore) -> None:
    store.append_soul_event(kind="turn.committed", payload={"surface": "text"})

    assert store.tail_soul_events(limit=0) == []
    assert store.tail_soul_events(kinds=set(), limit=10) == []
