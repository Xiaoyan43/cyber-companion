from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.memory.database import (
    ConversationSummaryRecord,
    FileAccessLogRecord,
    MemoryRecord,
    MessageRecord,
    MoodStateRecord,
    ReminderRecord,
    _row_to_memory,
    _row_to_message,
    _row_to_mood,
    connect,
    dumps_json,
    init_database,
    loads_json,
    resolve_db_path,
    utc_now_iso,
)
from backend.app.memory.schema import MEMORY_TYPES


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
            metadata=metadata if metadata is not None else current.metadata,
        )

        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE mood_state
                SET updated_at = ?, mood = ?, energy = ?, annoyance = ?, boredom = ?,
                    worry = ?, trust = ?, loneliness = ?, metadata_json = ?
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
