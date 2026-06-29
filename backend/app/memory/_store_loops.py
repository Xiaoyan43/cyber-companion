"""Soul-event log + open-loop (agenda) methods for MemoryStore."""

from __future__ import annotations

from typing import Any

from backend.app.memory._store_helpers import _clamp01, _normalize_aware_timestamp
from backend.app.memory.database import (
    OpenLoopRecord,
    SoulEventRecord,
    _row_to_open_loop,
    _row_to_soul_event,
    connect,
    dumps_json,
    utc_now_iso,
)
from backend.app.memory.schema import OPEN_LOOP_KINDS, OPEN_LOOP_STATUSES


class OpenLoopsAndEventsMixin:
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

    def create_open_loop(
        self,
        *,
        kind: str,
        title: str,
        summary: str = "",
        status: str = "open",
        due_at: str | None = None,
        last_mentioned_at: str | None = None,
        source_message_id: int | None = None,
        priority: float = 0.5,
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> OpenLoopRecord:
        if kind not in OPEN_LOOP_KINDS:
            raise ValueError(f"Unsupported open loop kind: {kind}")
        if status not in OPEN_LOOP_STATUSES:
            raise ValueError(f"Unsupported open loop status: {status}")
        normalized_due_at = _normalize_aware_timestamp(due_at, field_name="due_at")
        normalized_last_mentioned_at = _normalize_aware_timestamp(
            last_mentioned_at,
            field_name="last_mentioned_at",
        )

        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO open_loops (
                  status, kind, title, summary, due_at, last_mentioned_at,
                  source_message_id, priority, confidence, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    status,
                    kind,
                    title,
                    summary,
                    normalized_due_at,
                    normalized_last_mentioned_at,
                    source_message_id,
                    _clamp01(priority),
                    _clamp01(confidence),
                    dumps_json(metadata or {}),
                ),
            )
            loop_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM open_loops WHERE id = ?",
                (loop_id,),
            ).fetchone()
        assert row is not None
        return _row_to_open_loop(row)

    def get_open_loop(self, loop_id: int) -> OpenLoopRecord | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM open_loops WHERE id = ?",
                (loop_id,),
            ).fetchone()
        return _row_to_open_loop(row) if row else None

    def upsert_open_loop(
        self,
        *,
        loop_id: int | None = None,
        kind: str,
        title: str,
        summary: str = "",
        status: str = "open",
        due_at: str | None = None,
        last_mentioned_at: str | None = None,
        source_message_id: int | None = None,
        priority: float = 0.5,
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> OpenLoopRecord:
        """Update an existing loop by ``loop_id`` if it exists, else create one.

        Phase 3B-1 keeps the dedup key as the explicit ``id``; a natural-key
        fingerprint can be added additively when an off-path writer lands (Phase 6).
        """
        if loop_id is None or self.get_open_loop(loop_id) is None:
            return self.create_open_loop(
                kind=kind,
                title=title,
                summary=summary,
                status=status,
                due_at=due_at,
                last_mentioned_at=last_mentioned_at,
                source_message_id=source_message_id,
                priority=priority,
                confidence=confidence,
                metadata=metadata,
            )

        if kind not in OPEN_LOOP_KINDS:
            raise ValueError(f"Unsupported open loop kind: {kind}")
        if status not in OPEN_LOOP_STATUSES:
            raise ValueError(f"Unsupported open loop status: {status}")
        normalized_due_at = _normalize_aware_timestamp(due_at, field_name="due_at")
        normalized_last_mentioned_at = _normalize_aware_timestamp(
            last_mentioned_at,
            field_name="last_mentioned_at",
        )

        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE open_loops
                SET updated_at = ?, status = ?, kind = ?, title = ?, summary = ?,
                    due_at = ?, last_mentioned_at = ?, source_message_id = ?,
                    priority = ?, confidence = ?, metadata_json = ?
                WHERE id = ?
                """,
                (
                    utc_now_iso(),
                    status,
                    kind,
                    title,
                    summary,
                    normalized_due_at,
                    normalized_last_mentioned_at,
                    source_message_id,
                    _clamp01(priority),
                    _clamp01(confidence),
                    dumps_json(metadata or {}),
                    loop_id,
                ),
            )
        record = self.get_open_loop(loop_id)
        assert record is not None
        return record

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        due_before: str | None = None,
        limit: int = 50,
    ) -> list[OpenLoopRecord]:
        if limit <= 0:
            return []
        if status is not None and status not in OPEN_LOOP_STATUSES:
            raise ValueError(f"Unsupported open loop status: {status}")
        normalized_due_before = _normalize_aware_timestamp(
            due_before,
            field_name="due_before",
        )

        query = "SELECT * FROM open_loops"
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if normalized_due_before is not None:
            clauses.append("due_at IS NOT NULL AND julianday(due_at) <= julianday(?)")
            params.append(normalized_due_before)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        # Dated loops first (earliest due), then highest priority, then stable by id.
        query += (
            " ORDER BY (julianday(due_at) IS NULL), julianday(due_at) ASC,"
            " priority DESC, id ASC LIMIT ?"
        )
        params.append(limit)

        with connect(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_open_loop(row) for row in rows]

    def close_open_loop(self, loop_id: int) -> OpenLoopRecord | None:
        if self.get_open_loop(loop_id) is None:
            return None
        with connect(self.db_path) as connection:
            connection.execute(
                "UPDATE open_loops SET status = 'closed', updated_at = ? WHERE id = ?",
                (utc_now_iso(), loop_id),
            )
        return self.get_open_loop(loop_id)
