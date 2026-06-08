from pathlib import Path

import pytest

from backend.app.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "retention.db")


def test_prune_behavior_tick_messages_keeps_latest_and_preserves_chat(store: MemoryStore) -> None:
    store.create_message(role="user", content="real chat line")
    store.create_message(role="assistant", content="real reply")

    for index in range(15):
        store.create_message(
            role="assistant",
            content=f"tick-{index}",
            source="behavior_tick",
        )

    deleted = store.prune_behavior_tick_messages(5)

    assert deleted == 10
    assert store.count_chat_messages() == 2
    assert store.count_messages() == 7

    remaining_ticks = [
        message.content
        for message in store.list_messages(limit=20)
        if message.source == "behavior_tick"
    ]
    assert remaining_ticks == [f"tick-{index}" for index in range(10, 15)]


def test_prune_behavior_tick_messages_noop_when_keep_non_positive(store: MemoryStore) -> None:
    for index in range(3):
        store.create_message(
            role="assistant",
            content=f"tick-{index}",
            source="behavior_tick",
        )

    assert store.prune_behavior_tick_messages(0) == 0
    assert store.count_messages() == 3
