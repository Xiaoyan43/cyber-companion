"""Conversation summaries, reminders, and file-access-log methods for MemoryStore."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.memory.database import (
    ConversationSummaryRecord,
    FileAccessLogRecord,
    ReminderRecord,
    connect,
    dumps_json,
    loads_json,
)


class RecordsMixin:
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
