from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.memory.database import (
    ConversationSummaryRecord,
    FileAccessLogRecord,
    MemoryLinkRecord,
    MemoryRecord,
    MessageRecord,
    MoodStateRecord,
    RelationshipStateRecord,
    ReminderRecord,
    SoulEventRecord,
    _row_to_memory,
    _row_to_message,
    _row_to_mood,
    _row_to_relationship,
    _row_to_soul_event,
    connect,
    dumps_json,
    init_database,
    loads_json,
    resolve_db_path,
    utc_now_iso,
)
from backend.app.memory.schema import MEMORY_TYPES

_LINK_SNIPPET_MAX_LEN = 80


def _clip_link_snippet(content: str, max_len: int = _LINK_SNIPPET_MAX_LEN) -> str:
    trimmed = content.strip()
    if len(trimmed) <= max_len:
        return trimmed
    return trimmed[: max_len - 1].rstrip() + "…"


class MemoryStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = resolve_db_path(db_path)
        init_database(self.db_path)

    def create_message(
        self,
        *,
        role: str,
        content: str,
        source: str = "chat",
        metadata: dict[str, Any] | None = None,
    ) -> MessageRecord:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages (role, content, source, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (role, content, source, dumps_json(metadata or {})),
            )
            message_id = int(cursor.lastrowid)
            row = connection.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        assert row is not None
        return _row_to_message(row)

    def list_messages(self, *, limit: int = 50) -> list[MessageRecord]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM messages
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_message(row) for row in reversed(rows)]

    def count_messages(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM messages").fetchone()
        assert row is not None
        return int(row["total"])

    def count_chat_messages(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM messages WHERE source = 'chat'",
            ).fetchone()
        assert row is not None
        return int(row["total"])

    def get_last_user_chat_created_at(self) -> str | None:
        """Last user turn for post-conversation proactive cooldown.

        Includes text chat and RTC voice turns — both persist via
        ``persist_chat_turn`` with ``source='chat'`` (see ``turn_analyzer`` /
        ``companion_brain``).
        """
        with connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT created_at FROM messages
                WHERE source = 'chat' AND role = 'user'
                ORDER BY id DESC
                LIMIT 1
                """,
            ).fetchone()
        if row is None:
            return None
        return str(row["created_at"])

    def list_recent_chat_messages(self, limit: int) -> list[MessageRecord]:
        if limit <= 0:
            return []
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM messages
                WHERE source = 'chat'
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_message(row) for row in reversed(rows)]

    def list_chat_messages_between(
        self,
        after_id: int,
        before_id: int,
        limit: int,
    ) -> list[MessageRecord]:
        if limit <= 0:
            return []
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM messages
                WHERE source = 'chat' AND id > ? AND id < ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (after_id, before_id, limit),
            ).fetchall()
        return [_row_to_message(row) for row in rows]

    def prune_behavior_tick_messages(self, keep: int) -> int:
        if keep <= 0:
            return 0
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                DELETE FROM messages
                WHERE source = 'behavior_tick'
                  AND id NOT IN (
                    SELECT id FROM messages
                    WHERE source = 'behavior_tick'
                    ORDER BY id DESC
                    LIMIT ?
                  )
                """,
                (keep,),
            )
        return int(cursor.rowcount)

    def get_recent_chat_window_lower_bound_id(self, max_raw_turns: int) -> int | None:
        if max_raw_turns <= 0:
            return None
        with connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT id FROM messages
                WHERE source = 'chat'
                ORDER BY id DESC
                LIMIT 1 OFFSET ?
                """,
                (max_raw_turns - 1,),
            ).fetchone()
        return int(row["id"]) if row else None

    def _assistant_metadata_since(self, since: str) -> list[dict[str, Any]]:
        # `created_at` uses the SQLite `datetime('now')` format (UTC,
        # "YYYY-MM-DD HH:MM:SS"), which sorts lexicographically, so a string
        # `>=` comparison is a valid time filter and uses idx_messages_created_at.
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT metadata_json FROM messages
                WHERE role = 'assistant' AND created_at >= ?
                """,
                (since,),
            ).fetchall()
        return [loads_json(row["metadata_json"], {}) for row in rows]

    def sum_llm_cost_since(self, since: str) -> float:
        total = 0.0
        for metadata in self._assistant_metadata_since(since):
            cost = metadata.get("cost") or {}
            try:
                total += float(cost.get("total_usd", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
        return round(total, 8)

    def count_llm_turns_since(self, since: str) -> int:
        return sum(
            1
            for metadata in self._assistant_metadata_since(since)
            if metadata.get("should_call_llm") is True
        )

    def get_latest_conversation_summary(self) -> ConversationSummaryRecord | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT * FROM conversation_summaries
                ORDER BY range_end_message_id DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return ConversationSummaryRecord(
            id=row["id"],
            created_at=row["created_at"],
            range_start_message_id=row["range_start_message_id"],
            range_end_message_id=row["range_end_message_id"],
            summary=row["summary"],
            keywords=loads_json(row["keywords_json"], []),
        )

    def create_memory(
        self,
        *,
        type: str,
        content: str,
        tags: list[str] | None = None,
        importance: float = 0.5,
        confidence: float = 0.5,
        expires_at: str | None = None,
        source_message_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        if type not in MEMORY_TYPES:
            raise ValueError(f"Unsupported memory type: {type}")

        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO memories (
                  type, content, tags_json, importance, confidence,
                  expires_at, source_message_id, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    type,
                    content,
                    dumps_json(tags or []),
                    importance,
                    confidence,
                    expires_at,
                    source_message_id,
                    dumps_json(metadata or {}),
                ),
            )
            memory_id = int(cursor.lastrowid)
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        assert row is not None
        return _row_to_memory(row)

    def get_memory(self, memory_id: int) -> MemoryRecord | None:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return _row_to_memory(row) if row else None

    def list_memories(
        self,
        *,
        type: str | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        query = "SELECT * FROM memories"
        params: list[Any] = []

        if type is not None:
            if type not in MEMORY_TYPES:
                raise ValueError(f"Unsupported memory type: {type}")
            query += " WHERE type = ?"
            params.append(type)

        query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with connect(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_memory(row) for row in rows]

    def update_memory(
        self,
        memory_id: int,
        *,
        content: str | None = None,
        tags: list[str] | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord | None:
        existing = self.get_memory(memory_id)
        if existing is None:
            return None

        updated = MemoryRecord(
            id=existing.id,
            created_at=existing.created_at,
            updated_at=utc_now_iso(),
            type=existing.type,
            content=content if content is not None else existing.content,
            tags=tags if tags is not None else existing.tags,
            importance=importance if importance is not None else existing.importance,
            confidence=confidence if confidence is not None else existing.confidence,
            expires_at=expires_at if expires_at is not None else existing.expires_at,
            source_message_id=existing.source_message_id,
            metadata=metadata if metadata is not None else existing.metadata,
        )

        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE memories
                SET updated_at = ?, content = ?, tags_json = ?, importance = ?,
                    confidence = ?, expires_at = ?, metadata_json = ?
                WHERE id = ?
                """,
                (
                    updated.updated_at,
                    updated.content,
                    dumps_json(updated.tags),
                    updated.importance,
                    updated.confidence,
                    updated.expires_at,
                    dumps_json(updated.metadata),
                    memory_id,
                ),
            )
        return updated

    def delete_memory(self, memory_id: int) -> bool:
        with connect(self.db_path) as connection:
            cursor = connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return cursor.rowcount > 0

    def add_memory_link(
        self,
        memory_id: int,
        related_memory_id: int,
        relation: str = "related",
    ) -> None:
        # Store both directions so a single-direction lookup suffices at read time.
        # INSERT OR IGNORE keeps it idempotent via the UNIQUE(memory_id,
        # related_memory_id) constraint. No self-links.
        if memory_id == related_memory_id:
            return
        with connect(self.db_path) as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO memory_links (memory_id, related_memory_id, relation)
                VALUES (?, ?, ?)
                """,
                (
                    (memory_id, related_memory_id, relation),
                    (related_memory_id, memory_id, relation),
                ),
            )

    def get_linked_memory_ids(self, memory_id: int) -> list[int]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT related_memory_id FROM memory_links WHERE memory_id = ? ORDER BY id",
                (memory_id,),
            ).fetchall()
        return [int(row["related_memory_id"]) for row in rows]

    def count_memory_links(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT COUNT(*) AS n FROM memory_links").fetchone()
        return int(row["n"]) if row else 0

    def list_memory_links(self, limit: int = 100) -> list[MemoryLinkRecord]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    ml.id,
                    ml.memory_id,
                    ml.related_memory_id,
                    ml.relation,
                    ml.created_at,
                    a.type AS memory_type,
                    a.content AS memory_content,
                    b.type AS related_type,
                    b.content AS related_content
                FROM memory_links ml
                JOIN memories a ON a.id = ml.memory_id
                JOIN memories b ON b.id = ml.related_memory_id
                WHERE ml.memory_id < ml.related_memory_id
                ORDER BY ml.id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            MemoryLinkRecord(
                id=int(row["id"]),
                memory_id=int(row["memory_id"]),
                related_memory_id=int(row["related_memory_id"]),
                relation=str(row["relation"]),
                created_at=str(row["created_at"]),
                memory_type=str(row["memory_type"]),
                memory_content=_clip_link_snippet(str(row["memory_content"])),
                related_type=str(row["related_type"]),
                related_content=_clip_link_snippet(str(row["related_content"])),
            )
            for row in rows
        ]

    def append_soul_event(
        self,
        *,
        kind: str,
        payload: dict[str, Any] | None = None,
    ) -> SoulEventRecord:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO soul_events (kind, payload_json)
                VALUES (?, ?)
                """,
                (kind, dumps_json(payload or {})),
            )
            event_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM soul_events WHERE id = ?",
                (event_id,),
            ).fetchone()
        assert row is not None
        return _row_to_soul_event(row)

    def tail_soul_events(
        self,
        *,
        kinds: set[str] | None = None,
        limit: int = 50,
    ) -> list[SoulEventRecord]:
        if limit <= 0:
            return []
        if kinds is not None and not kinds:
            return []

        query = "SELECT * FROM soul_events"
        params: list[Any] = []
        if kinds is not None:
            placeholders = ",".join("?" for _ in kinds)
            query += f" WHERE kind IN ({placeholders})"
            params.extend(sorted(kinds))
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with connect(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_soul_event(row) for row in reversed(rows)]

    def get_mood_state(self) -> MoodStateRecord:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM mood_state WHERE id = 1").fetchone()
        assert row is not None
        return _row_to_mood(row)

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
        gap_feeling: float | None = None,
        box_relation: float | None = None,
        self_ease: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MoodStateRecord:
        current = self.get_mood_state()
        updated = MoodStateRecord(
            updated_at=utc_now_iso(),
            mood=mood if mood is not None else current.mood,
            energy=energy if energy is not None else current.energy,
            annoyance=annoyance if annoyance is not None else current.annoyance,
            boredom=boredom if boredom is not None else current.boredom,
            worry=worry if worry is not None else current.worry,
            trust=trust if trust is not None else current.trust,
            loneliness=loneliness if loneliness is not None else current.loneliness,
            gap_feeling=gap_feeling if gap_feeling is not None else current.gap_feeling,
            box_relation=box_relation if box_relation is not None else current.box_relation,
            self_ease=self_ease if self_ease is not None else current.self_ease,
            metadata=metadata if metadata is not None else current.metadata,
        )

        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE mood_state
                SET updated_at = ?, mood = ?, energy = ?, annoyance = ?, boredom = ?,
                    worry = ?, trust = ?, loneliness = ?, gap_feeling = ?,
                    box_relation = ?, self_ease = ?, metadata_json = ?
                WHERE id = 1
                """,
                (
                    updated.updated_at,
                    updated.mood,
                    updated.energy,
                    updated.annoyance,
                    updated.boredom,
                    updated.worry,
                    updated.trust,
                    updated.loneliness,
                    updated.gap_feeling,
                    updated.box_relation,
                    updated.self_ease,
                    dumps_json(updated.metadata),
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

    def create_conversation_summary(
        self,
        *,
        range_start_message_id: int,
        range_end_message_id: int,
        summary: str,
        keywords: list[str] | None = None,
    ) -> ConversationSummaryRecord:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO conversation_summaries (
                  range_start_message_id, range_end_message_id, summary, keywords_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    range_start_message_id,
                    range_end_message_id,
                    summary,
                    dumps_json(keywords or []),
                ),
            )
            summary_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM conversation_summaries WHERE id = ?",
                (summary_id,),
            ).fetchone()
        assert row is not None
        return ConversationSummaryRecord(
            id=row["id"],
            created_at=row["created_at"],
            range_start_message_id=row["range_start_message_id"],
            range_end_message_id=row["range_end_message_id"],
            summary=row["summary"],
            keywords=loads_json(row["keywords_json"], []),
        )

    def create_reminder(
        self,
        *,
        title: str,
        details: str = "",
        due_at: str | None = None,
        status: str = "pending",
        source_message_id: int | None = None,
    ) -> ReminderRecord:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO reminders (title, details, due_at, status, source_message_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, details, due_at, status, source_message_id),
            )
            reminder_id = int(cursor.lastrowid)
            row = connection.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
        assert row is not None
        return ReminderRecord(
            id=row["id"],
            created_at=row["created_at"],
            due_at=row["due_at"],
            title=row["title"],
            details=row["details"],
            status=row["status"],
            source_message_id=row["source_message_id"],
        )

    def find_due_reminder(self, *, now: datetime | None = None) -> ReminderRecord | None:
        aware = now if now is not None else datetime.now(timezone.utc)
        if aware.tzinfo is None:
            aware = aware.replace(tzinfo=timezone.utc)
        now_iso = aware.astimezone(timezone.utc).isoformat()

        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM reminders
                WHERE status = 'pending' AND due_at IS NOT NULL AND due_at <= ?
                ORDER BY due_at ASC, id ASC
                LIMIT 5
                """,
                (now_iso,),
            ).fetchall()

        if not rows:
            return None
        row = rows[0]
        return ReminderRecord(
            id=row["id"],
            created_at=row["created_at"],
            due_at=row["due_at"],
            title=row["title"],
            details=row["details"],
            status=row["status"],
            source_message_id=row["source_message_id"],
        )

    def log_file_access(
        self,
        *,
        operation: str,
        requested_path: str,
        resolved_path: str,
        allowed: bool,
        reason: str = "",
    ) -> FileAccessLogRecord:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO file_access_log (
                  operation, requested_path, resolved_path, allowed, reason
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (operation, requested_path, resolved_path, int(allowed), reason),
            )
            log_id = int(cursor.lastrowid)
            row = connection.execute("SELECT * FROM file_access_log WHERE id = ?", (log_id,)).fetchone()
        assert row is not None
        return FileAccessLogRecord(
            id=row["id"],
            created_at=row["created_at"],
            operation=row["operation"],
            requested_path=row["requested_path"],
            resolved_path=row["resolved_path"],
            allowed=bool(row["allowed"]),
            reason=row["reason"],
        )

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO schema_meta(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def note_llm_turn(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'turns_since_reflection'",
            ).fetchone()
            current = int(row["value"]) if row else 0
            new_count = current + 1
            connection.execute(
                """
                INSERT INTO schema_meta(key, value) VALUES ('turns_since_reflection', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(new_count),),
            )
        return new_count

    def claim_reflection(self, threshold: int) -> bool:
        with connect(self.db_path) as connection:
            turns_row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'turns_since_reflection'",
            ).fetchone()
            reflecting_row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'reflecting'",
            ).fetchone()
            turns = int(turns_row["value"]) if turns_row else 0
            reflecting = reflecting_row["value"] if reflecting_row else "0"
            if reflecting != "1" and turns >= threshold:
                connection.execute(
                    """
                    INSERT INTO schema_meta(key, value) VALUES ('reflecting', '1')
                    ON CONFLICT(key) DO UPDATE SET value = '1'
                    """
                )
                connection.execute(
                    """
                    INSERT INTO schema_meta(key, value) VALUES ('turns_since_reflection', '0')
                    ON CONFLICT(key) DO UPDATE SET value = '0'
                    """
                )
                return True
            return False

    def release_reflection(self) -> None:
        self.set_meta("reflecting", "0")

    @staticmethod
    def _turn_analyzing_key(room_id: str) -> str:
        return f"turn_analyzing:{room_id.strip()}"

    def claim_turn_analysis(self, room_id: str) -> bool:
        key = self._turn_analyzing_key(room_id)
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = ?",
                (key,),
            ).fetchone()
            if row and str(row["value"]) == "1":
                return False
            connection.execute(
                """
                INSERT INTO schema_meta(key, value) VALUES (?, '1')
                ON CONFLICT(key) DO UPDATE SET value = '1'
                """,
                (key,),
            )
            return True

    def release_turn_analysis(self, room_id: str) -> None:
        self.set_meta(self._turn_analyzing_key(room_id), "0")

    def get_max_chat_message_id(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT MAX(id) AS max_id FROM messages WHERE source = 'chat'",
            ).fetchone()
        if row is None or row["max_id"] is None:
            return 0
        return int(row["max_id"])

    def list_file_access_logs(self, *, limit: int = 50) -> list[FileAccessLogRecord]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM file_access_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            FileAccessLogRecord(
                id=row["id"],
                created_at=row["created_at"],
                operation=row["operation"],
                requested_path=row["requested_path"],
                resolved_path=row["resolved_path"],
                allowed=bool(row["allowed"]),
                reason=row["reason"],
            )
            for row in reversed(rows)
        ]


_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


def reset_memory_store() -> None:
    global _store
    _store = None
