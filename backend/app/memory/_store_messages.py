"""Messages + LLM cost/turn accounting methods for MemoryStore."""

from __future__ import annotations

from typing import Any

from backend.app.memory.database import (
    MessageRecord,
    _row_to_message,
    connect,
    dumps_json,
    loads_json,
)


class MessagesMixin:
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

    def get_max_chat_message_id(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT MAX(id) AS max_id FROM messages WHERE source = 'chat'",
            ).fetchone()
        if row is None or row["max_id"] is None:
            return 0
        return int(row["max_id"])
