from pathlib import Path

import pytest

from backend.app.memory.database import connect, dumps_json, init_database, loads_json
from backend.app.memory.schema import (
    OPERATIONAL_MOOD_METADATA_KEYS,
    RETIRED_RELATIONSHIP_GUARD_METADATA_KEYS,
)
from backend.app.memory.store import MemoryStore


_V7_UPDATED_AT = "2026-06-20T03:04:05+00:00"


def _operational_fixture() -> dict[str, object]:
    return {
        "last_proactive_check_at": "2026-06-20T01:00:00+00:00",
        "idle_experience_last_at": "2026-06-20T00:30:00+00:00",
        "idle_experience_daily_date": "2026-06-20",
        "idle_experience_daily_count": 1,
        "proactive_recent_fingerprints": ["check_in:none"],
        "share_recent_memory_ids": [7],
        "idle_experience_recent_material_ids": ["weather:rain"],
    }


def _simulate_v7_database(db_path: Path) -> dict[str, object]:
    init_database(db_path)
    operational = _operational_fixture()
    legacy = {
        **operational,
        **{key: "retired" for key in RETIRED_RELATIONSHIP_GUARD_METADATA_KEYS},
        "positive_zone_streak": 2,
        "unrelated_legacy_key": "preserve",
    }
    with connect(db_path) as connection:
        connection.execute("DROP TABLE behavior_runtime_state")
        connection.execute(
            "DELETE FROM schema_meta WHERE key = 'behavior_runtime_state_v1_backfilled'"
        )
        connection.execute(
            "DELETE FROM schema_meta WHERE key = 'relationship_guard_metadata_v1_purged'"
        )
        connection.execute("UPDATE schema_meta SET value = '7' WHERE key = 'schema_version'")
        connection.execute(
            "UPDATE mood_state SET updated_at = ?, metadata_json = ? WHERE id = 1",
            (_V7_UPDATED_AT, dumps_json(legacy)),
        )
    return operational


def test_v7_runtime_backfill_is_exact_filtered_and_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "v7.db"
    operational = _simulate_v7_database(db_path)

    init_database(db_path)
    store = MemoryStore(db_path=db_path)
    runtime = store.get_behavior_runtime_state()
    assert runtime.updated_at == _V7_UPDATED_AT
    assert runtime.metadata == operational
    assert set(runtime.metadata) == OPERATIONAL_MOOD_METADATA_KEYS

    patched = store.patch_behavior_runtime_metadata(
        updates={"idle_experience_daily_count": 9}
    )
    init_database(db_path)
    after_rerun = store.get_behavior_runtime_state()
    assert after_rerun.updated_at == patched.updated_at
    assert after_rerun.metadata["idle_experience_daily_count"] == 9

    mood_metadata = store.get_mood_state().metadata
    assert RETIRED_RELATIONSHIP_GUARD_METADATA_KEYS.isdisjoint(mood_metadata)


def test_canonical_runtime_wins_while_mood_view_preserves_local_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "canonical-runtime.db"
    _simulate_v7_database(db_path)
    store = MemoryStore(db_path=db_path)

    store.patch_behavior_runtime_metadata(updates={"idle_experience_daily_count": 4})
    with connect(db_path) as connection:
        legacy = loads_json(
            connection.execute(
                "SELECT metadata_json FROM mood_state WHERE id = 1"
            ).fetchone()["metadata_json"],
            {},
        )
        legacy["idle_experience_daily_count"] = 999
        connection.execute(
            "UPDATE mood_state SET metadata_json = ? WHERE id = 1",
            (dumps_json(legacy),),
        )

    merged = store.get_mood_state().metadata
    assert merged["idle_experience_daily_count"] == 4
    assert merged["positive_zone_streak"] == 2
    assert merged["unrelated_legacy_key"] == "preserve"


def test_runtime_patch_and_remove_dual_write_legacy_copy(tmp_path: Path) -> None:
    store = MemoryStore(db_path=tmp_path / "dual-write.db")
    store.replace_mood_metadata(
        {
            "positive_zone_streak": 2,
            "share_recent_memory_ids": [7],
            "last_proactive_check_at": "old-check",
        }
    )

    runtime = store.patch_behavior_runtime_metadata(
        updates={"last_proactive_check_at": "new-check"},
        remove=("share_recent_memory_ids",),
    )
    assert runtime.metadata == {"last_proactive_check_at": "new-check"}

    with connect(store.db_path) as connection:
        legacy = loads_json(
            connection.execute(
                "SELECT metadata_json FROM mood_state WHERE id = 1"
            ).fetchone()["metadata_json"],
            {},
        )
    assert legacy == {
        "positive_zone_streak": 2,
        "last_proactive_check_at": "new-check",
    }


def test_local_metadata_patch_does_not_overwrite_runtime(tmp_path: Path) -> None:
    store = MemoryStore(db_path=tmp_path / "local-patch.db")
    store.patch_behavior_runtime_metadata(updates={"idle_experience_daily_count": 3})
    store.patch_mood_metadata(updates={"positive_zone_streak": 2})

    assert store.get_behavior_runtime_state().metadata == {"idle_experience_daily_count": 3}
    assert store.get_mood_state().metadata == {
        "positive_zone_streak": 2,
        "idle_experience_daily_count": 3,
    }


def test_runtime_patch_rejects_non_operational_keys(tmp_path: Path) -> None:
    store = MemoryStore(db_path=tmp_path / "invalid-patch.db")
    with pytest.raises(ValueError, match="Non-operational"):
        store.patch_behavior_runtime_metadata(updates={"positive_zone_streak": 2})


def test_retired_relationship_guard_keys_cannot_reenter_metadata(tmp_path: Path) -> None:
    store = MemoryStore(db_path=tmp_path / "retired-guards.db")

    replaced = store.replace_mood_metadata(
        {
            "positive_zone_streak": 2,
            "proactive_pending_since": "must-not-return",
        }
    )
    assert replaced.metadata == {"positive_zone_streak": 2}

    with pytest.raises(ValueError, match="Retired relationship guard"):
        store.patch_mood_metadata(updates={"proactive_daily_count": 1})
