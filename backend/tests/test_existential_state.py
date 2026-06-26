from pathlib import Path

import pytest

from backend.app.memory.context_builder import _GAP_PHRASES, build_provider_context
from backend.app.memory.database import connect, init_database
from backend.app.memory.store import MemoryStore


_V6_UPDATED_AT = "2026-05-01T02:03:04+00:00"


def _simulate_v6_database(db_path: Path) -> None:
    init_database(db_path)
    with connect(db_path) as connection:
        connection.execute("DROP TABLE existential_state")
        connection.execute(
            "DELETE FROM schema_meta WHERE key = 'existential_state_v1_backfilled'"
        )
        connection.execute(
            "UPDATE schema_meta SET value = '6' WHERE key = 'schema_version'"
        )
        connection.execute(
            """
            UPDATE mood_state
            SET updated_at = ?, gap_feeling = 0.73, box_relation = 0.41, self_ease = 0.62
            WHERE id = 1
            """,
            (_V6_UPDATED_AT,),
        )


def test_v6_existential_backfill_is_exact_and_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "v6.db"
    _simulate_v6_database(db_path)

    init_database(db_path)
    store = MemoryStore(db_path=db_path)
    state = store.get_existential_state()
    assert state.updated_at == _V6_UPDATED_AT
    assert state.gap_feeling == pytest.approx(0.73)
    assert state.box_relation == pytest.approx(0.41)
    assert state.self_ease == pytest.approx(0.62)

    updated = store.update_existential_state(gap_feeling=0.91)
    with connect(db_path) as connection:
        connection.execute("UPDATE mood_state SET gap_feeling = 0.12 WHERE id = 1")
    init_database(db_path)
    after_rerun = store.get_existential_state()
    assert after_rerun.updated_at == updated.updated_at
    assert after_rerun.gap_feeling == pytest.approx(0.91)


def test_mood_updates_leave_legacy_existential_columns_unchanged(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-columns.db"
    _simulate_v6_database(db_path)
    store = MemoryStore(db_path=db_path)

    store.update_mood_state(annoyance=0.8, metadata={"positive_zone_streak": 2})

    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT gap_feeling, box_relation, self_ease FROM mood_state WHERE id = 1"
        ).fetchone()
    assert row is not None
    assert tuple(row) == pytest.approx((0.73, 0.41, 0.62))


def test_context_builder_reads_canonical_existential_state(tmp_path: Path) -> None:
    store = MemoryStore(db_path=tmp_path / "canonical.db")
    store.update_existential_state(gap_feeling=0.1, box_relation=0.5, self_ease=0.5)
    with connect(store.db_path) as connection:
        connection.execute("UPDATE mood_state SET gap_feeling = 0.95 WHERE id = 1")

    system = build_provider_context(store, user_input="hello").messages[0].content
    assert _GAP_PHRASES["low"] in system
    assert _GAP_PHRASES["high"] not in system
