"""Mood / relationship / existential / behavior-runtime state methods (the kernel)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from backend.app.memory._store_helpers import _clamp01
from backend.app.memory.database import (
    BehaviorRuntimeStateRecord,
    ExistentialStateRecord,
    MoodStateRecord,
    RelationshipStateRecord,
    _row_to_behavior_runtime,
    _row_to_existential,
    _row_to_mood,
    _row_to_relationship,
    connect,
    dumps_json,
    loads_json,
    utc_now_iso,
)
from backend.app.memory.schema import (
    OPERATIONAL_MOOD_METADATA_KEYS,
    RETIRED_RELATIONSHIP_GUARD_METADATA_KEYS,
)


class StateMixin:
    def get_mood_state(self) -> MoodStateRecord:
        with connect(self.db_path) as connection:
            mood_row = connection.execute("SELECT * FROM mood_state WHERE id = 1").fetchone()
            relationship_row = connection.execute(
                "SELECT trust FROM relationship_state WHERE id = 1"
            ).fetchone()
            runtime_row = connection.execute(
                "SELECT * FROM behavior_runtime_state WHERE id = 1"
            ).fetchone()
        assert mood_row is not None
        assert relationship_row is not None
        assert runtime_row is not None
        mood = _row_to_mood(mood_row)
        runtime = _row_to_behavior_runtime(runtime_row)
        merged_metadata = {
            key: value
            for key, value in mood.metadata.items()
            if key not in OPERATIONAL_MOOD_METADATA_KEYS
            and key not in RETIRED_RELATIONSHIP_GUARD_METADATA_KEYS
        }
        merged_metadata.update(runtime.metadata)
        return replace(
            mood,
            trust=float(relationship_row["trust"]),
            metadata=merged_metadata,
        )

    def get_behavior_runtime_state(self) -> BehaviorRuntimeStateRecord:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM behavior_runtime_state WHERE id = 1"
            ).fetchone()
        assert row is not None
        return _row_to_behavior_runtime(row)

    def patch_behavior_runtime_metadata(
        self,
        *,
        updates: dict[str, Any] | None = None,
        remove: tuple[str, ...] = (),
    ) -> BehaviorRuntimeStateRecord:
        patch = updates or {}
        invalid = (set(patch) | set(remove)) - OPERATIONAL_MOOD_METADATA_KEYS
        if invalid:
            raise ValueError(f"Non-operational behavior runtime keys: {sorted(invalid)}")

        updated_at = utc_now_iso()
        with connect(self.db_path) as connection:
            runtime_row = connection.execute(
                "SELECT metadata_json FROM behavior_runtime_state WHERE id = 1"
            ).fetchone()
            mood_row = connection.execute(
                "SELECT metadata_json FROM mood_state WHERE id = 1"
            ).fetchone()
            assert runtime_row is not None
            assert mood_row is not None

            runtime_metadata = loads_json(runtime_row["metadata_json"], {})
            if not isinstance(runtime_metadata, dict):
                runtime_metadata = {}
            runtime_metadata.update(patch)
            for key in remove:
                runtime_metadata.pop(key, None)

            legacy_metadata = loads_json(mood_row["metadata_json"], {})
            if not isinstance(legacy_metadata, dict):
                legacy_metadata = {}
            for key in OPERATIONAL_MOOD_METADATA_KEYS | RETIRED_RELATIONSHIP_GUARD_METADATA_KEYS:
                legacy_metadata.pop(key, None)
            legacy_metadata.update(runtime_metadata)

            connection.execute(
                """
                UPDATE behavior_runtime_state
                SET updated_at = ?, metadata_json = ?
                WHERE id = 1
                """,
                (updated_at, dumps_json(runtime_metadata)),
            )
            connection.execute(
                """
                UPDATE mood_state
                SET updated_at = ?, metadata_json = ?
                WHERE id = 1
                """,
                (updated_at, dumps_json(legacy_metadata)),
            )
        return BehaviorRuntimeStateRecord(updated_at=updated_at, metadata=runtime_metadata)

    def patch_mood_metadata(
        self,
        *,
        updates: dict[str, Any] | None = None,
        remove: tuple[str, ...] = (),
    ) -> MoodStateRecord:
        patch = updates or {}
        retired = (set(patch) | set(remove)) & RETIRED_RELATIONSHIP_GUARD_METADATA_KEYS
        if retired:
            raise ValueError(f"Retired relationship guard keys: {sorted(retired)}")
        invalid = (set(patch) | set(remove)) & OPERATIONAL_MOOD_METADATA_KEYS
        if invalid:
            raise ValueError(f"Operational keys require runtime patch API: {sorted(invalid)}")

        updated_at = utc_now_iso()
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT metadata_json FROM mood_state WHERE id = 1"
            ).fetchone()
            assert row is not None
            metadata = loads_json(row["metadata_json"], {})
            if not isinstance(metadata, dict):
                metadata = {}
            metadata.update(patch)
            for key in remove:
                metadata.pop(key, None)
            connection.execute(
                "UPDATE mood_state SET updated_at = ?, metadata_json = ? WHERE id = 1",
                (updated_at, dumps_json(metadata)),
            )
        return self.get_mood_state()

    def replace_mood_metadata(self, metadata: dict[str, Any]) -> MoodStateRecord:
        cleaned_metadata = {
            key: value
            for key, value in metadata.items()
            if key not in RETIRED_RELATIONSHIP_GUARD_METADATA_KEYS
        }
        runtime_metadata = {
            key: value
            for key, value in cleaned_metadata.items()
            if key in OPERATIONAL_MOOD_METADATA_KEYS
        }
        updated_at = utc_now_iso()
        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE behavior_runtime_state
                SET updated_at = ?, metadata_json = ?
                WHERE id = 1
                """,
                (updated_at, dumps_json(runtime_metadata)),
            )
            # Keep the complete compatibility view in the legacy column. This is the
            # rollback copy; canonical reads filter operational keys back through the
            # behavior_runtime_state row above.
            connection.execute(
                "UPDATE mood_state SET updated_at = ?, metadata_json = ? WHERE id = 1",
                (updated_at, dumps_json(cleaned_metadata)),
            )
        return self.get_mood_state()

    def get_existential_state(self) -> ExistentialStateRecord:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM existential_state WHERE id = 1").fetchone()
        assert row is not None
        return _row_to_existential(row)

    def update_existential_state(
        self,
        *,
        gap_feeling: float | None = None,
        box_relation: float | None = None,
        self_ease: float | None = None,
    ) -> ExistentialStateRecord:
        current = self.get_existential_state()
        updated = ExistentialStateRecord(
            updated_at=utc_now_iso(),
            gap_feeling=_clamp01(
                gap_feeling if gap_feeling is not None else current.gap_feeling
            ),
            box_relation=_clamp01(
                box_relation if box_relation is not None else current.box_relation
            ),
            self_ease=_clamp01(self_ease if self_ease is not None else current.self_ease),
        )
        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE existential_state
                SET updated_at = ?, gap_feeling = ?, box_relation = ?, self_ease = ?
                WHERE id = 1
                """,
                (
                    updated.updated_at,
                    updated.gap_feeling,
                    updated.box_relation,
                    updated.self_ease,
                ),
            )
        return updated

    def update_mood_state(
        self,
        *,
        mood: str | None = None,
        energy: float | None = None,
        annoyance: float | None = None,
        boredom: float | None = None,
        worry: float | None = None,
        trust: float | None = None,
        loneliness: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MoodStateRecord:
        if trust is not None:
            self.update_relationship_state(trust=trust)
        if metadata is not None:
            self.replace_mood_metadata(metadata)
        current = self.get_mood_state()
        updated = MoodStateRecord(
            updated_at=utc_now_iso(),
            mood=mood if mood is not None else current.mood,
            energy=energy if energy is not None else current.energy,
            annoyance=annoyance if annoyance is not None else current.annoyance,
            boredom=boredom if boredom is not None else current.boredom,
            worry=worry if worry is not None else current.worry,
            trust=current.trust,
            loneliness=loneliness if loneliness is not None else current.loneliness,
            metadata=current.metadata,
        )

        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE mood_state
                SET updated_at = ?, mood = ?, energy = ?, annoyance = ?, boredom = ?,
                    worry = ?, loneliness = ?
                WHERE id = 1
                """,
                (
                    updated.updated_at,
                    updated.mood,
                    updated.energy,
                    updated.annoyance,
                    updated.boredom,
                    updated.worry,
                    updated.loneliness,
                ),
            )
        return updated

    def get_relationship_state(self) -> RelationshipStateRecord:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM relationship_state WHERE id = 1").fetchone()
        assert row is not None
        return _row_to_relationship(row)

    def update_relationship_state(
        self,
        *,
        trust: float | None = None,
        closeness: float | None = None,
        familiarity: float | None = None,
        tension: float | None = None,
        last_meaningful_interaction_at: str | None = ...,  # type: ignore[assignment]
        metadata: dict[str, Any] | None = None,
    ) -> RelationshipStateRecord:
        current = self.get_relationship_state()

        def _clamp(value: float) -> float:
            return max(0.0, min(1.0, value))

        meaningful_at = current.last_meaningful_interaction_at
        if last_meaningful_interaction_at is not ...:
            meaningful_at = last_meaningful_interaction_at

        updated = RelationshipStateRecord(
            updated_at=utc_now_iso(),
            trust=_clamp(trust if trust is not None else current.trust),
            closeness=_clamp(closeness if closeness is not None else current.closeness),
            familiarity=_clamp(familiarity if familiarity is not None else current.familiarity),
            tension=_clamp(tension if tension is not None else current.tension),
            last_meaningful_interaction_at=meaningful_at,
            metadata=metadata if metadata is not None else current.metadata,
        )

        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE relationship_state
                SET updated_at = ?, trust = ?, closeness = ?, familiarity = ?,
                    tension = ?, last_meaningful_interaction_at = ?, metadata_json = ?
                WHERE id = 1
                """,
                (
                    updated.updated_at,
                    updated.trust,
                    updated.closeness,
                    updated.familiarity,
                    updated.tension,
                    updated.last_meaningful_interaction_at,
                    dumps_json(updated.metadata),
                ),
            )
        return updated
