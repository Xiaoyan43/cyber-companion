from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.memory.store import MemoryStore
from backend.app.soul.adapters import NoopAgendaPort, SQLiteAgendaPort, ports_from_store
from backend.app.soul.ports import OpenLoopDraft


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "open_loops.db")


def _now() -> datetime:
    return datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc)


# --- store CRUD -------------------------------------------------------------


def test_create_open_loop_round_trip_and_defaults(store: MemoryStore) -> None:
    loop = store.create_open_loop(kind="follow_up", title="问问面试结果")

    assert loop.id == 1
    assert loop.kind == "follow_up"
    assert loop.title == "问问面试结果"
    assert loop.status == "open"
    assert loop.summary == ""
    assert loop.due_at is None
    assert loop.last_mentioned_at is None
    assert loop.source_message_id is None
    assert loop.priority == 0.5
    assert loop.confidence == 0.5
    assert loop.metadata == {}
    assert loop.created_at
    assert loop.updated_at

    fetched = store.get_open_loop(loop.id)
    assert fetched == loop


def test_create_open_loop_persists_all_fields(store: MemoryStore) -> None:
    message = store.create_message(role="user", content="周四要面试")
    due = (_now() + timedelta(days=1)).isoformat()
    loop = store.create_open_loop(
        kind="future_event",
        title="周四面试",
        summary="13:00 远程",
        due_at=due,
        last_mentioned_at=_now().isoformat(),
        source_message_id=message.id,
        priority=0.9,
        confidence=0.8,
        metadata={"topic": "job"},
    )
    assert loop.summary == "13:00 远程"
    assert loop.due_at == due
    assert loop.source_message_id == message.id
    assert loop.priority == 0.9
    assert loop.confidence == 0.8
    assert loop.metadata == {"topic": "job"}


def test_create_open_loop_clamps_priority_and_confidence(store: MemoryStore) -> None:
    loop = store.create_open_loop(
        kind="commitment",
        title="too hot",
        priority=2.0,
        confidence=-1.0,
    )
    assert loop.priority == 1.0
    assert loop.confidence == 0.0


def test_create_open_loop_rejects_bad_kind(store: MemoryStore) -> None:
    with pytest.raises(ValueError):
        store.create_open_loop(kind="nonsense", title="x")


def test_create_open_loop_rejects_bad_status(store: MemoryStore) -> None:
    with pytest.raises(ValueError):
        store.create_open_loop(kind="commitment", title="x", status="archived")


def test_list_open_loops_filters_by_status(store: MemoryStore) -> None:
    first = store.create_open_loop(kind="commitment", title="open one")
    store.create_open_loop(kind="commitment", title="snoozed one", status="snoozed")
    store.close_open_loop(first.id)
    later = store.create_open_loop(kind="commitment", title="still open")

    open_ids = [loop.id for loop in store.list_open_loops(status="open")]
    assert open_ids == [later.id]

    snoozed = store.list_open_loops(status="snoozed")
    assert [loop.title for loop in snoozed] == ["snoozed one"]

    # status=None returns every status.
    assert len(store.list_open_loops(status=None)) == 3


def test_list_open_loops_due_before_filters_and_orders(store: MemoryStore) -> None:
    now = _now()
    overdue = store.create_open_loop(
        kind="future_event",
        title="overdue",
        due_at=(now - timedelta(hours=2)).isoformat(),
        priority=0.3,
    )
    due_now = store.create_open_loop(
        kind="future_event",
        title="just due",
        due_at=(now - timedelta(minutes=1)).isoformat(),
        priority=0.9,
    )
    store.create_open_loop(
        kind="future_event",
        title="future",
        due_at=(now + timedelta(days=1)).isoformat(),
    )
    store.create_open_loop(kind="commitment", title="no due date")

    due = store.list_open_loops(status="open", due_before=now.isoformat())
    # Only the two due/overdue loops, earliest-due first (overdue before just-due).
    assert [loop.id for loop in due] == [overdue.id, due_now.id]


def test_list_open_loops_orders_dated_then_priority(store: MemoryStore) -> None:
    now = _now()
    dated = store.create_open_loop(
        kind="future_event",
        title="dated",
        due_at=(now + timedelta(days=2)).isoformat(),
        priority=0.1,
    )
    high = store.create_open_loop(kind="commitment", title="high prio", priority=0.9)
    low = store.create_open_loop(kind="commitment", title="low prio", priority=0.2)

    ordered = [loop.id for loop in store.list_open_loops(status="open")]
    # Dated loop first, then undated by priority desc.
    assert ordered == [dated.id, high.id, low.id]


def test_list_open_loops_limit_and_zero(store: MemoryStore) -> None:
    for i in range(3):
        store.create_open_loop(kind="commitment", title=f"loop {i}")
    assert len(store.list_open_loops(status="open", limit=2)) == 2
    assert store.list_open_loops(status="open", limit=0) == []


def test_close_open_loop(store: MemoryStore) -> None:
    loop = store.create_open_loop(kind="commitment", title="to close")
    closed = store.close_open_loop(loop.id)
    assert closed is not None
    assert closed.status == "closed"
    assert store.list_open_loops(status="open") == []
    assert store.close_open_loop(999) is None


def test_upsert_open_loop_creates_without_id(store: MemoryStore) -> None:
    loop = store.upsert_open_loop(kind="user_goal", title="learn rust")
    assert loop.id == 1
    assert loop.kind == "user_goal"


def test_upsert_open_loop_updates_existing_by_id(store: MemoryStore) -> None:
    loop = store.create_open_loop(kind="commitment", title="draft", priority=0.4)
    updated = store.upsert_open_loop(
        loop_id=loop.id,
        kind="commitment",
        title="final",
        summary="refined",
        priority=0.8,
        status="snoozed",
    )
    assert updated.id == loop.id
    assert updated.title == "final"
    assert updated.summary == "refined"
    assert updated.priority == 0.8
    assert updated.status == "snoozed"
    # No duplicate row created.
    assert len(store.list_open_loops(status=None)) == 1


def test_upsert_open_loop_creates_when_id_missing(store: MemoryStore) -> None:
    created = store.upsert_open_loop(loop_id=42, kind="commitment", title="ghost id")
    assert created.id == 1  # fell back to create, fresh autoincrement id


# --- AgendaPort -------------------------------------------------------------


def test_sqlite_agenda_port_round_trip(store: MemoryStore) -> None:
    port = SQLiteAgendaPort(store)
    created = port.upsert(OpenLoopDraft(kind="follow_up", title="ping back", priority=0.7))
    assert created is not None
    assert created.id == 1

    loops = port.open_loops(status="open")
    assert [loop.title for loop in loops] == ["ping back"]

    closed = port.close(created.id)
    assert closed is not None and closed.status == "closed"
    assert port.open_loops(status="open") == []


def test_sqlite_agenda_port_upsert_updates_existing(store: MemoryStore) -> None:
    port = SQLiteAgendaPort(store)
    created = port.upsert(OpenLoopDraft(kind="commitment", title="v1"))
    assert created is not None
    updated = port.upsert(OpenLoopDraft(kind="commitment", title="v2", loop_id=created.id))
    assert updated is not None and updated.title == "v2"
    assert len(store.list_open_loops(status=None)) == 1


def test_ports_from_store_wires_sqlite_agenda(store: MemoryStore) -> None:
    ports = ports_from_store(store)
    assert isinstance(ports.agenda, SQLiteAgendaPort)
    store.create_open_loop(kind="commitment", title="via store")
    assert [loop.title for loop in ports.agenda.open_loops()] == ["via store"]


def test_noop_agenda_port_is_inert() -> None:
    port = NoopAgendaPort()
    assert port.open_loops() == []
    assert port.upsert(OpenLoopDraft(kind="commitment", title="ignored")) is None
    assert port.close(1) is None
